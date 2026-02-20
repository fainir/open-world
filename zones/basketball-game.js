import * as THREE from 'three';
export default class BasketballGame{
  constructor(api){this.api=api;this.group=null;this.ball=null;this.ballVel=new THREE.Vector3();
    this.score=0;this.timeLeft=60;this.state='playing';this.hudEl=null;
    this.hasBall=true;this.shotPower=0;this.charging=false;this.playerX=0;this.playerZ=0}
  async enter(group,zone){
    this.group=group;this.score=0;this.timeLeft=60;this.state='playing';this.hasBall=true;
    const{box,cyl}=this.api;
    // Court
    const court=new THREE.Mesh(new THREE.PlaneGeometry(15,28),new THREE.MeshStandardMaterial({color:0xcc7744,roughness:.6}));
    court.rotation.x=-Math.PI/2;group.add(court);
    // Lines
    const lnM=new THREE.MeshStandardMaterial({color:0xffffff});
    const mkL=(x,z,w,d)=>{const l=new THREE.Mesh(new THREE.PlaneGeometry(w,d),lnM);l.rotation.x=-Math.PI/2;l.position.set(x,.01,z);group.add(l)};
    mkL(0,0,15,.1);mkL(0,-14,15,.1);mkL(0,14,15,.1);mkL(-7.5,0,.1,28);mkL(7.5,0,.1,28);
    // Center circle
    const cc=new THREE.Mesh(new THREE.RingGeometry(1.8,1.95,16),lnM);cc.rotation.x=-Math.PI/2;cc.position.set(0,.01,0);group.add(cc);
    // Hoop at -Z end
    const pole=cyl(.08,.08,3.5,0x888888);pole.position.set(0,1.75,-13.5);group.add(pole);
    const bb=box(1.2,.8,.05,0xffffff);bb.position.set(0,3.2,-13.5);group.add(bb);
    this.rim=new THREE.Mesh(new THREE.TorusGeometry(.23,.02,6,12),new THREE.MeshStandardMaterial({color:0xff4400}));
    this.rim.rotation.x=Math.PI/2;this.rim.position.set(0,3,-13.2);group.add(this.rim);
    // Ball
    this.ball=new THREE.Mesh(new THREE.SphereGeometry(.12,8,6),new THREE.MeshStandardMaterial({color:0xff8833}));
    this.ball.position.set(0,1,5);group.add(this.ball);
    // Lighting
    group.add(new THREE.AmbientLight(0xffffff,.7));
    const sun=new THREE.DirectionalLight(0xffffff,.6);sun.position.set(3,8,5);group.add(sun);
    // HUD
    this.hudEl=document.createElement('div');this.hudEl.id='mission-hud';
    this.hudEl.style.cssText='position:fixed;top:20px;left:50%;transform:translateX(-50%);color:#fff;font-family:"Courier New",monospace;font-size:1.3em;background:rgba(0,0,0,0.6);padding:8px 20px;border-radius:8px;z-index:7';
    document.body.appendChild(this.hudEl);
    // Power bar
    this.powerEl=document.createElement('div');this.powerEl.style.cssText='position:fixed;bottom:80px;left:50%;transform:translateX(-50%);width:200px;height:8px;background:rgba(255,255,255,0.2);border-radius:4px;z-index:7';
    const fill=document.createElement('div');fill.style.cssText='width:0%;height:100%;background:linear-gradient(90deg,#44ff44,#ff4444);border-radius:4px;transition:width 0.05s';
    this.powerEl.appendChild(fill);this.powerFill=fill;
    document.body.appendChild(this.powerEl);
    this.playerX=0;this.playerZ=5;
    this.api.P.set(group.position.x,group.position.y+1.7,group.position.z+5);
    this.api.V.set(0,0,0);this.api.mode='walk';
    this._updateHUD();
    this.api.showTip('Basketball! Hold Click to charge, release to shoot. 60 seconds!');
  }
  _updateHUD(){if(this.hudEl)this.hudEl.textContent=`SCORE: ${this.score} | TIME: ${Math.max(0,this.timeLeft|0)}s`}
  update(dt){
    if(this.state==='done')return;
    this.timeLeft-=dt;
    if(this.timeLeft<=0){this.state='done';this.api.showTip(`Time! Final score: ${this.score}`);this._updateHUD();return}
    const gp=this.group.position;
    // Player movement
    const{keys}=this.api;const spd=8;
    if(keys['KeyA']||keys['ArrowLeft'])this.playerX=Math.max(this.playerX-spd*dt,-6);
    if(keys['KeyD']||keys['ArrowRight'])this.playerX=Math.min(this.playerX+spd*dt,6);
    if(keys['KeyW']||keys['ArrowUp'])this.playerZ=Math.max(this.playerZ-spd*dt,-12);
    if(keys['KeyS']||keys['ArrowDown'])this.playerZ=Math.min(this.playerZ+spd*dt,12);
    this.api.P.set(gp.x+this.playerX,gp.y+1.7,gp.z+this.playerZ);
    // Shooting mechanic
    if(this.hasBall){
      this.ball.position.set(this.playerX+.3,1.5,this.playerZ);
      // Mouse down = charge
      if(keys['mouse0']||keys['_shooting']){if(!this.charging){this.charging=true;this.shotPower=0}
        this.shotPower=Math.min(this.shotPower+dt*1.5,1);
        this.powerFill.style.width=(this.shotPower*100)+'%'}
      else if(this.charging){
        // Release = shoot
        this.charging=false;
        const power=this.shotPower;this.shotPower=0;this.powerFill.style.width='0%';
        const hoopDx=0-this.playerX,hoopDz=-13.2-this.playerZ;
        const dist=Math.sqrt(hoopDx*hoopDx+hoopDz*hoopDz);
        const t=dist/(12+power*8);
        this.ballVel.set(hoopDx/t,(5+power*3)/t,hoopDz/t);
        this.hasBall=false}}
    // Ball physics
    if(!this.hasBall){
      this.ball.position.add(this.ballVel.clone().multiplyScalar(dt));
      this.ballVel.y-=15*dt;
      // Check score (near rim)
      const bx=this.ball.position.x,bz=this.ball.position.z,by=this.ball.position.y;
      if(Math.abs(bx)<.4&&Math.abs(bz-(-13.2))<.4&&by<3.1&&by>2.7&&this.ballVel.y<0){
        this.score+=2;this._updateHUD();this.api.showTip('SCORE! +2');
        this.hasBall=true;this.ball.position.set(this.playerX,1.5,this.playerZ);this.ballVel.set(0,0,0)}
      // Ball hits ground
      if(by<.12){this.ball.position.y=.12;this.ballVel.y=Math.abs(this.ballVel.y)*.5;this.ballVel.x*=.8;this.ballVel.z*=.8;
        if(this.ballVel.length()<.5){this.hasBall=true;this.ballVel.set(0,0,0)}}
      // Backboard bounce
      if(Math.abs(bx)<.7&&bz<-13.3&&by>2&&by<3.5){this.ballVel.z=Math.abs(this.ballVel.z)*.4}}
    this._updateHUD();
    // Camera
    const cam=this.api.cam;
    cam.position.set(gp.x+this.playerX*.3,gp.y+8,gp.z+this.playerZ+10);
    cam.lookAt(gp.x,gp.y,gp.z-5);
  }
  async exit(){if(this.hudEl){this.hudEl.remove();this.hudEl=null}
    if(this.powerEl){this.powerEl.remove();this.powerEl=null}this.ball=null}
}
