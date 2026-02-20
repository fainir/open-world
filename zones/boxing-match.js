import * as THREE from 'three';
export default class BoxingMatch{
  constructor(api){this.api=api;this.group=null;this.playerHP=100;this.oppHP=100;
    this.state='fighting';this.oppX=0;this.oppZ=0;this.playerX=0;this.playerZ=0;
    this.hudEl=null;this.cooldown=0;this.oppCooldown=0;this.oppState='idle';this.oppTimer=0;
    this.hitFlash=0}
  async enter(group,zone){
    this.group=group;this.playerHP=100;this.oppHP=100;this.state='fighting';
    const{box,cyl}=this.api;
    // Ring floor
    const floor=box(7,.8,7,0xdddddd);floor.position.y=.4;group.add(floor);
    const mat=new THREE.Mesh(new THREE.PlaneGeometry(6,6),new THREE.MeshStandardMaterial({color:0x224488}));
    mat.rotation.x=-Math.PI/2;mat.position.y=.82;group.add(mat);
    // Ring posts & ropes
    for(const rx of[-3,3])for(const rz of[-3,3]){
      const post=cyl(.08,.08,1.8,0xcccccc);post.position.set(rx,1.7,rz);group.add(post)}
    for(let rh=0;rh<3;rh++){const ry=1.1+rh*.3;const rc=[0xff0000,0xffffff,0x0000ff][rh];
      for(const[sx,sz,len,axis] of[[3,0,6,'z'],[0,3,6,'x'],[-3,0,6,'z'],[0,-3,6,'x']]){
        const rope=cyl(.02,.02,len,rc);
        if(axis==='x')rope.rotation.z=Math.PI/2;else rope.rotation.x=Math.PI/2;
        rope.position.set(sx,ry,sz);group.add(rope)}}
    // Opponent
    this.oppMesh=new THREE.Group();
    const oBody=cyl(.25,.2,1,0xff4444);oBody.position.y=1.3;this.oppMesh.add(oBody);
    const oHead=new THREE.Mesh(new THREE.SphereGeometry(.15,6,5),new THREE.MeshStandardMaterial({color:0xddbb99}));
    oHead.position.y=2;this.oppMesh.add(oHead);
    // Gloves
    for(const gx of[-.35,.35]){const gl=new THREE.Mesh(new THREE.SphereGeometry(.1,6,5),new THREE.MeshStandardMaterial({color:0xff2222}));
      gl.position.set(gx,1.5,.25);this.oppMesh.add(gl)}
    this.oppMesh.position.set(0,.82,-1.5);group.add(this.oppMesh);
    this.oppX=0;this.oppZ=-1.5;
    // Lighting
    group.add(new THREE.AmbientLight(0xffffff,.5));
    const spot=new THREE.PointLight(0xffffff,1.5,15);spot.position.set(0,5,0);group.add(spot);
    // HUD
    this.hudEl=document.createElement('div');this.hudEl.id='mission-hud';
    this.hudEl.style.cssText='position:fixed;top:20px;left:50%;transform:translateX(-50%);color:#fff;font-family:"Courier New",monospace;font-size:1.1em;background:rgba(0,0,0,0.6);padding:8px 16px;border-radius:8px;z-index:7;display:flex;gap:20px';
    document.body.appendChild(this.hudEl);
    this.playerX=0;this.playerZ=1.5;
    this.api.P.set(group.position.x,group.position.y+2.5,group.position.z+1.5);
    this.api.V.set(0,0,0);this.api.mode='walk';
    this._updateHUD();
    this.api.showTip('Boxing! Click to punch, WASD to move & dodge');
  }
  _updateHUD(){
    if(!this.hudEl)return;
    const phc=this.playerHP>50?'#44ff44':this.playerHP>25?'#ffaa00':'#ff4444';
    const ohc=this.oppHP>50?'#44ff44':this.oppHP>25?'#ffaa00':'#ff4444';
    this.hudEl.innerHTML=`<span>YOU <span style="color:${phc}">${this.playerHP|0}</span></span><span>VS</span><span>OPP <span style="color:${ohc}">${this.oppHP|0}</span></span>`;
  }
  update(dt){
    if(this.state!=='fighting'){
      const cam=this.api.cam,gp=this.group.position;
      cam.position.set(gp.x+5,gp.y+4,gp.z+5);cam.lookAt(gp.x,gp.y+2,gp.z);return}
    const gp=this.group.position;
    this.cooldown=Math.max(0,this.cooldown-dt);
    this.oppCooldown=Math.max(0,this.oppCooldown-dt);
    this.hitFlash=Math.max(0,this.hitFlash-dt*3);
    // Player movement
    const{keys}=this.api;const spd=5;
    if(keys['KeyA']||keys['ArrowLeft'])this.playerX=Math.max(this.playerX-spd*dt,-2.5);
    if(keys['KeyD']||keys['ArrowRight'])this.playerX=Math.min(this.playerX+spd*dt,2.5);
    if(keys['KeyW']||keys['ArrowUp'])this.playerZ=Math.max(this.playerZ-spd*dt,-2.5);
    if(keys['KeyS']||keys['ArrowDown'])this.playerZ=Math.min(this.playerZ+spd*dt,2.5);
    this.api.P.set(gp.x+this.playerX,gp.y+2.5,gp.z+this.playerZ);
    // Player punch
    if((keys['mouse0']||keys['_shooting'])&&this.cooldown<=0){
      keys['mouse0']=false;keys['_shooting']=false;
      this.cooldown=.5;
      const dx=this.oppX-this.playerX,dz=this.oppZ-this.playerZ;
      if(Math.sqrt(dx*dx+dz*dz)<1.5){
        const dmg=10+Math.random()*10;this.oppHP-=dmg;this.hitFlash=1;
        if(this.oppHP<=0){this.oppHP=0;this.state='won';this.api.showTip('KO! You win! +500 pts')}
        this._updateHUD()}}
    // Opponent AI
    this.oppTimer+=dt;
    if(this.oppState==='idle'){
      // Move toward player
      const dx=this.playerX-this.oppX,dz=this.playerZ-this.oppZ;
      const dist=Math.sqrt(dx*dx+dz*dz);
      if(dist>1){const s=3*dt/dist;this.oppX+=dx*s;this.oppZ+=dz*s}
      else if(this.oppCooldown<=0){this.oppState='punching';this.oppTimer=0}}
    if(this.oppState==='punching'){
      if(this.oppTimer>.3){// Land punch
        const dx=this.playerX-this.oppX,dz=this.playerZ-this.oppZ;
        if(Math.sqrt(dx*dx+dz*dz)<1.8){
          const dmg=8+Math.random()*8;this.playerHP-=dmg;
          if(this.playerHP<=0){this.playerHP=0;this.state='lost';this.api.showTip('Knocked out! Better luck next time')}
          this._updateHUD()}
        this.oppState='idle';this.oppCooldown=1+Math.random()}}
    this.oppX=this.api.clamp(this.oppX,-2.5,2.5);this.oppZ=this.api.clamp(this.oppZ,-2.5,2.5);
    this.oppMesh.position.set(this.oppX,.82,this.oppZ);
    this.oppMesh.lookAt(gp.x+this.playerX,2,gp.z+this.playerZ);
    // Camera
    const cam=this.api.cam;
    cam.position.set(gp.x+this.playerX*.3,gp.y+4,gp.z+this.playerZ+4);
    cam.lookAt(gp.x+(this.playerX+this.oppX)/2,gp.y+2,gp.z+(this.playerZ+this.oppZ)/2);
  }
  async exit(){if(this.hudEl){this.hudEl.remove();this.hudEl=null}this.oppMesh=null}
}
