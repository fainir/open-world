import * as THREE from 'three';
export default class TennisMatch{
  constructor(api){this.api=api;this.group=null;this.ball=null;this.ballVel=new THREE.Vector3();
    this.playerScore=0;this.opponentScore=0;this.state='serving';this.stateTimer=0;
    this.oppX=0;this.oppZ=0;this.hudEl=null;this.playerZ=0;this.playerX=0}
  async enter(group,zone){
    this.group=group;this.playerScore=0;this.opponentScore=0;this.state='serving';this.stateTimer=0;
    const{box,cyl}=this.api;
    // Court surface
    const court=new THREE.Mesh(new THREE.PlaneGeometry(11,24),new THREE.MeshStandardMaterial({color:0x2266aa,roughness:.6}));
    court.rotation.x=-Math.PI/2;group.add(court);
    // Lines
    const lnM=new THREE.MeshStandardMaterial({color:0xffffff});
    const mkL=(x,z,w,d)=>{const l=new THREE.Mesh(new THREE.PlaneGeometry(w,d),lnM);l.rotation.x=-Math.PI/2;l.position.set(x,.01,z);group.add(l)};
    mkL(0,0,11,.1);mkL(0,-12,11,.1);mkL(0,12,11,.1);mkL(-5.5,0,.1,24);mkL(5.5,0,.1,24);
    mkL(0,-6,11,.08);mkL(0,6,11,.08);mkL(0,0,.08,24);
    // Net
    const np1=cyl(.04,.04,1.2,0x888888);np1.position.set(-6,.6,0);group.add(np1);
    const np2=cyl(.04,.04,1.2,0x888888);np2.position.set(6,.6,0);group.add(np2);
    const net=new THREE.Mesh(new THREE.PlaneGeometry(12,1),new THREE.MeshStandardMaterial({color:0xffffff,transparent:true,opacity:.5,side:THREE.DoubleSide}));
    net.position.set(0,.7,0);group.add(net);
    // Ball
    this.ball=new THREE.Mesh(new THREE.SphereGeometry(.06,8,6),new THREE.MeshStandardMaterial({color:0xccff00}));
    this.ball.position.set(0,1,8);group.add(this.ball);
    // Opponent (simple figure)
    const oppG=new THREE.Group();
    const oppBody=cyl(.2,.15,.8,0xff4444);oppBody.position.y=.9;oppG.add(oppBody);
    const oppHead=new THREE.Mesh(new THREE.SphereGeometry(.12,6,5),new THREE.MeshStandardMaterial({color:0xddbb99}));
    oppHead.position.y=1.45;oppG.add(oppHead);
    const racket=box(.3,.01,.2,0x44aa44);racket.position.set(.25,1,-.15);oppG.add(racket);
    oppG.position.set(0,0,-8);group.add(oppG);this.oppMesh=oppG;
    this.oppX=0;this.oppZ=-8;
    // Fence
    const fenceM=new THREE.MeshStandardMaterial({color:0x888888,transparent:true,opacity:.3,side:THREE.DoubleSide});
    for(const fz of[-13,13]){const f=new THREE.Mesh(new THREE.PlaneGeometry(14,3),fenceM);f.position.set(0,1.5,fz);group.add(f)}
    for(const fx of[-7,7]){const f=new THREE.Mesh(new THREE.PlaneGeometry(26,3),fenceM);f.rotation.y=Math.PI/2;f.position.set(fx,1.5,0);group.add(f)}
    // Lighting
    group.add(new THREE.AmbientLight(0xffffff,.7));
    const sun=new THREE.DirectionalLight(0xffffff,.8);sun.position.set(5,10,5);group.add(sun);
    // HUD
    this.hudEl=document.createElement('div');this.hudEl.id='mission-hud';
    this.hudEl.style.cssText='position:fixed;top:20px;left:50%;transform:translateX(-50%);color:#fff;font-family:"Courier New",monospace;font-size:1.3em;background:rgba(0,0,0,0.6);padding:8px 20px;border-radius:8px;z-index:7';
    document.body.appendChild(this.hudEl);
    // Camera & player setup
    this.playerX=0;this.playerZ=8;
    this.api.P.set(group.position.x,group.position.y+1.5,group.position.z+8);
    this.api.V.set(0,0,0);this.api.mode='walk';
    this._serve(true);this._updateHUD();
    this.api.showTip('Tennis! Click to hit ball. First to 5 wins!');
  }
  _serve(playerServing){
    this.state='serving';this.stateTimer=0;
    if(playerServing){this.ball.position.set(0,1.5,8);this.ballVel.set(0,0,0)}
    else{this.ball.position.set(this.oppX,1.5,this.oppZ);this.ballVel.set((Math.random()-.5)*3,4,8)}
  }
  _updateHUD(){if(this.hudEl)this.hudEl.textContent=`YOU ${this.playerScore} - ${this.opponentScore} OPP | First to 5`}
  _point(forPlayer){
    if(forPlayer)this.playerScore++;else this.opponentScore++;
    this._updateHUD();
    if(this.playerScore>=5){this.state='won';this.api.showTip('You WIN! +500 pts');return}
    if(this.opponentScore>=5){this.state='lost';this.api.showTip('You lost! Try again next time');return}
    this.state='pause';this.stateTimer=0;
  }
  update(dt){
    this.stateTimer+=dt;
    const gp=this.group.position;
    // Player movement
    const{keys}=this.api;const spd=10;
    if(keys['KeyA']||keys['ArrowLeft'])this.playerX=Math.max(this.playerX-spd*dt,-5);
    if(keys['KeyD']||keys['ArrowRight'])this.playerX=Math.min(this.playerX+spd*dt,5);
    if(keys['KeyW']||keys['ArrowUp'])this.playerZ=Math.max(this.playerZ-spd*dt,2);
    if(keys['KeyS']||keys['ArrowDown'])this.playerZ=Math.min(this.playerZ+spd*dt,11);
    this.api.P.set(gp.x+this.playerX,gp.y+1.5,gp.z+this.playerZ);
    // Click to hit
    if(this.api.keys['_shooting']||this.api.keys['mouse0']){this.api.keys['_shooting']=false;this.api.keys['mouse0']=false;
      if(this.state==='serving'){const dx=(Math.random()-.5)*3;this.ballVel.set(dx,5,-12);this.ball.position.set(this.playerX,1.2,this.playerZ);this.state='rally'}
      else if(this.state==='rally'){const bx=this.ball.position.x-this.playerX,bz=this.ball.position.z-this.playerZ;
        if(Math.abs(bx)<2&&Math.abs(bz)<2&&this.ball.position.z>0){this.ballVel.set((Math.random()-.5)*4,4,-10+Math.random()*2)}}}
    // Ball physics
    if(this.state==='rally'||this.state==='serving'&&this.ballVel.length()>0){
      this.ball.position.add(this.ballVel.clone().multiplyScalar(dt));
      this.ballVel.y-=12*dt;
      // Bounce
      if(this.ball.position.y<.06){this.ball.position.y=.06;this.ballVel.y=Math.abs(this.ballVel.y)*.6;
        if(this.ballVel.y<.5){// Ball stopped bouncing
          if(this.ball.position.z<0)this._point(true);else this._point(false)}}
      // Out of bounds
      if(Math.abs(this.ball.position.x)>7||this.ball.position.z<-14||this.ball.position.z>14){
        if(this.ball.position.z<0)this._point(true);else this._point(false)}
      // Opponent AI hit
      if(this.ball.position.z<-5&&this.ball.position.y<2&&this.ballVel.z<0){
        const dist=Math.abs(this.ball.position.x-this.oppX);
        if(dist<2.5){this.ballVel.set((Math.random()-.5)*4,4+Math.random()*2,10+Math.random()*3)}}}
    // Opponent movement
    if(this.state==='rally'){const target=this.ball.position.x;
      this.oppX+=(target-this.oppX)*3*dt;this.oppX=this.api.clamp(this.oppX,-5,5);
      this.oppMesh.position.x=this.oppX}
    // Pause between points
    if(this.state==='pause'&&this.stateTimer>1.5)this._serve(this.stateTimer%2<1);
    // Camera (overhead angled)
    const cam=this.api.cam;
    cam.position.set(gp.x,gp.y+12,gp.z+16);cam.lookAt(gp.x,gp.y,gp.z);
  }
  async exit(){if(this.hudEl){this.hudEl.remove();this.hudEl=null}this.ball=null;this.oppMesh=null}
}
