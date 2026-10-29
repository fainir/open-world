"""Caller-owned account exports and closure; no credentials leave this module."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import zipfile
import time
from collections import OrderedDict,deque

from fastapi import HTTPException

from app.backend.models import ChatSession, ChatMessage, GameVersion, Star
from app.backend.recovery import (PUBLICATION_LOCK, read_deleted_accounts,
                                  write_deleted_accounts, purge_account)

_EXPORTS = threading.BoundedSemaphore(2)
_ACCOUNT_LIMIT_LOCK=threading.Lock()
_ACCOUNT_BUCKETS=OrderedDict()


def account_action(user_id):
    # Scope costly account actions to the authenticated account, not a shared household IP.
    with _ACCOUNT_LIMIT_LOCK:
        now=time.monotonic();bucket=_ACCOUNT_BUCKETS.pop(user_id,deque())
        while bucket and bucket[0]<=now-3600:bucket.popleft()
        _ACCOUNT_BUCKETS[user_id]=bucket
        while len(_ACCOUNT_BUCKETS)>10000:_ACCOUNT_BUCKETS.popitem(last=False)
        if len(bucket)>=8:raise HTTPException(429,'Too many account-data actions. Please try again later.',headers={'Retry-After':'3600'})
        bucket.append(now)



def export_account(db, user, data_dir, versions_dir):
    if not _EXPORTS.acquire(blocking=False):
        raise HTTPException(503, 'An export is being prepared. Please try again shortly.')
    output = None
    try:
        with PUBLICATION_LOCK:
            sessions=db.query(ChatSession).filter_by(user_id=user.id).all()
            session_ids=[item.id for item in sessions]
            messages=db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).order_by(ChatMessage.created_at).all()
            versions=db.query(GameVersion).filter(GameVersion.session_id.in_(session_ids)).order_by(GameVersion.created_at).all()
            stars=db.query(Star).filter_by(user_id=user.id).all()
            payload={
                'format':'openworld-account','version':1,
                'profile':{'id':user.id,'email':user.email,'username':user.username,'created_at':user.created_at},
                'sessions':[{'id':item.id,'created_at':item.created_at} for item in sessions],
                'messages':[{'id':item.id,'session_id':item.session_id,'role':item.role,'content':item.content,'created_at':item.created_at} for item in messages],
                'versions':[{key:getattr(item,key) for key in ('id','session_id','version_number','description','parent_version_id','is_shared','share_slug','is_published','publish_title','is_suggested','suggestion_status','user_prompt','created_at')} for item in versions],
                'stars':[{'version_id':item.version_id,'created_at':item.created_at} for item in stars]
            }
            files=[]
            for version in versions:
                path=Path(versions_dir)/version.file_path
                if path.name!=version.file_path or path.is_symlink() or not path.is_file():
                    raise HTTPException(503,'A saved game is unavailable. Your data is unchanged; please contact support.')
                files.append((version.id,path))
            if sum(path.stat().st_size for _,path in files)>512*1024**2:
                raise HTTPException(413,'This export needs operator assistance because it exceeds 512 MB. Contact support for a complete copy.')
            folder=Path(data_dir)/'exports';folder.mkdir(mode=0o700,exist_ok=True)
            descriptor,name=tempfile.mkstemp(prefix='export-',suffix='.zip',dir=folder);os.close(descriptor)
            output=Path(name);os.chmod(output,0o600)
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('account.json',json.dumps(payload,default=lambda value:value.isoformat()))
                for version_id,path in files:archive.write(path,'games/'+version_id+'.html')
            return output
    except Exception:
        if output:output.unlink(missing_ok=True)
        raise
    finally:
        _EXPORTS.release()


def _commit_deletion(connection):
    connection.commit()


def delete_account(user_id, data_dir, versions_dir):
    """Rollback both rows and files on a normal failure. Durable intent closes crash gaps."""
    data_dir,versions_dir=Path(data_dir),Path(versions_dir)
    directory=data_dir/'account-removals'/hashlib.sha256(user_id.encode()).hexdigest()
    moved=[];committed=False;intent_written=False;created=False
    with PUBLICATION_LOCK, closing(sqlite3.connect(data_dir/'openworld.db')) as connection:
        previous=read_deleted_accounts(data_dir,create=True)
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN IMMEDIATE')
        try:
            if not connection.execute('SELECT 1 FROM users WHERE id=?',(user_id,)).fetchone():
                raise HTTPException(401,'Sign in again to check this account.')
            names=purge_account(connection,user_id)
            # A crash after this durable intent is reconciled before startup traffic.
            write_deleted_accounts(data_dir,previous|{user_id});intent_written=True
            directory.parent.mkdir(mode=0o700,exist_ok=True)
            directory.mkdir(mode=0o700,exist_ok=False);created=True
            for name in names:
                source=versions_dir/name
                if source.is_symlink():raise RuntimeError('Invalid owned game file')
                if source.exists():
                    destination=directory/name;os.replace(source,destination);moved.append((source,destination))
            _commit_deletion(connection);committed=True
        except Exception:
            connection.rollback()
            for source,destination in reversed(moved):
                if destination.exists():os.replace(destination,source)
            if intent_written:write_deleted_accounts(data_dir,previous)
            raise
        finally:
            if created and directory.exists() and (committed or not any(path.exists() for _,path in moved)):
                shutil.rmtree(directory)
