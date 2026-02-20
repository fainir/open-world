import * as THREE from 'three';
export default class ArcheryChallenge{
  constructor(api){this.api=api;this.group=null;this.score=0;this.arrows=10;
    this.state='playing';this.hudEl=null;this.aimX=0;this.aimY=1.5;
    this.activeArrow=null;this.arrowVel=null;this.cooldown=0;this.targets=[];this.crosshair=null}
  async enter(group,zone){
    this.group=group;this.score=0;this.arrows=10;this.state='playing';this.cooldown=0;
    const{box,cyl}=this.api;
    // Ground
    const gnd=new THREE.Mesh(new THREE.PlaneGeometry(20,20),new THREE.MeshStandardMaterial({color:0x3a7a3a,roughness:.8}));
    gnd.rotation.x=-Math.PI/2;group.add(gnd);
    // Targets (3)
    this.targets=[];
    for(let t=0;t<3;t++){const tx=-4+t*4,tz=-8;
      const tG=new THREE.Group();
      // Stand
      const stand=cyl(.04,.04,2,0x6a4a2a);stand.position.set(0,1,0);tG.add(stand);
      // Target face
      const white=new THREE.Mesh(new THREE.CircleGeometry(1,16),new THREE.MeshStandardMaterial({color:0xffffff}));
      white.position.set(0,1.5,.01);tG.add(white);
      const blue=new THREE.Mesh(new THREE.RingGeometry(.6,1,16),new THREE.MeshStandardMaterial({color:0x0066ff}));
      blue.position.set(0,1.5,.02);tG.add(blue);
      const red=new THREE.Mesh(new THREE.RingGeometry(.3,.6,16),new THREE.MeshStandardMaterial({color:0xff0000}));
      red.position.set(0,1.5,.03);tG.add(red);
      const bull=new THREE.Mesh(new THREE.CircleGeometry(.3,12),new THREE.MeshStandardMaterial({color:0xffdd00}));
      bull.position.set(0,1.5,.04);tG.add(bull);
      const inner=new THREE.Mesh(new THREE.CircleGeometry(.1,8),new THREE.MeshStandardMaterial({color:0xffdd00,emissive:0xffdd00,emissiveIntensity:.5}));
      inner.position.set(0,1.5,.05);tG.add(inner);
      tG.position.set(tx,0,tz);group.add(tG);
      this.targets.push({group:tG,x:tx,z:tz,y:1.5})}
    // Shooting line
    const line=new THREE.Mesh(new THREE.PlaneGeometry(12,.08),new THREE.MeshStandardMaterial({color:0xffffff}));
    line.rotation.x=-Math.PI/2;line.position.set(0,.01,5);group.add(line);
    // Safety net behind targets
    const net=new THREE.Mesh(new THREE.PlaneGeometry(16,4),new THREE.MeshStandardMaterial({color:0x888888,transparent:true,opacity:.3,side:THREE.DoubleSide}));
    net.position.set(0,2,-9.5);group.add(net);
    // Crosshair
    this.crosshair=document.createElement('div');
    this.crosshair.style.cssText='position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);color:#ff4444;font-size:28px;font-family:monospace;z-index:7;pointer-events:none';
    this.crosshair.textContent='+';document.body.appendChild(this.crosshair);
    // Lighting
    group.add(new THREE.AmbientLight(0xffffff,.7));
    const sun=new THREE.DirectionalLight(0xffffff,.8);sun.position.set(3,8,5);group.add(sun);
    // HUD
    this.hudEl=document.createElement('div');this.hudEl.id='mission-hud';
    this.hudEl.style.cssText='position:fixed;top:20px;left:50%;transform:translateX(-50%);color:#fff;font-family:"Courier New",monospace;font-size:1.3em;background:rgba(0,0,0,0.6);padding:8px 20px;border-radius:8px;z-index:7';
    document.body.appendChild(this.hudEl);
    this.api.P.set(group.position.x,group.position.y+1.7,group.position.z+5);
    this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
    this._updateHUD();
    this.api.showTip('Archery! Aim with mouse, click to shoot. 10 arrows!');
  }
  _updateHUD(){if(this.hudEl)this.hudEl.textContent=`SCORE: ${this.score} | ARROWS: ${this.arrows}`}
  update(dt){
    if(this.state==='done'){
      const cam=this.api.cam,gp=this.group.position;
      cam.position.set(gp.x,gp.y+5,gp.z+8);cam.lookAt(gp.x,gp.y+1.5,gp.z-8);return}
    this.cooldown=Math.max(0,this.cooldown-dt);
    const gp=this.group.position;
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    // First person aiming
    P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
    // Shoot
    if((keys['mouse0']||keys['_shooting'])&&this.cooldown<=0&&this.arrows>0&&!this.activeArrow){
      keys['mouse0']=false;keys['_shooting']=false;
      this.cooldown=.8;this.arrows--;
      // Create arrow
      const arrow=new THREE.Mesh(new THREE.CylinderGeometry(.01,.01,.8,4),new THREE.MeshStandardMaterial({color:0x6a4a2a}));
      arrow.rotation.x=Math.PI/2;
      const dir=new THREE.Vector3(-Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),-Math.cos(yaw)*Math.cos(pitch)).normalize();
      arrow.position.copy(P);
      group.add(arrow);group.worldToLocal(arrow.position);
      this.activeArrow=arrow;
      this.arrowVel=dir.multiplyScalar(30);
      this._updateHUD()}
    // Arrow physics
    if(this.activeArrow){
      const lv=this.arrowVel.clone().multiplyScalar(dt);
      this.activeArrow.position.add(lv);
      this.arrowVel.y-=5*dt;
      // Check target hits
      const ap=this.activeArrow.position;
      for(const t of this.targets){
        const dx=ap.x-t.x,dy=ap.y-t.y,dz=ap.z-t.z;
        if(Math.abs(dz)<.3&&Math.sqrt(dx*dx+dy*dy)<1.2){
          // Hit! Score based on distance from center
          const dist=Math.sqrt(dx*dx+dy*dy);
          let pts=0;
          if(dist<.1)pts=10;else if(dist<.3)pts=8;else if(dist<.6)pts=5;else if(dist<1)pts=3;else pts=1;
          this.score+=pts;
          this.api.showTip(pts>=8?'BULLSEYE! +'+pts:'+'+pts+' points');
          // Stick arrow in target
          this.activeArrow.position.z=t.z+.1;
          this.activeArrow=null;this.arrowVel=null;
          this._updateHUD();break}}
      // Miss (hit ground or too far)
      if(this.activeArrow&&(ap.y<-.5||ap.z<-12||ap.z>10)){
        group.remove(this.activeArrow);
        this.activeArrow.geometry.dispose();this.activeArrow.material.dispose();
        this.activeArrow=null;this.arrowVel=null;
        this.api.showTip('Miss!')}}
    // Check game over
    if(this.arrows<=0&&!this.activeArrow&&this.state==='playing'){
      this.state='done';
      this.api.showTip(`Archery complete! Final score: ${this.score}`)}
  }
  async exit(){
    if(this.hudEl){this.hudEl.remove();this.hudEl=null}
    if(this.crosshair){this.crosshair.remove();this.crosshair=null}
    this.targets=[];this.activeArrow=null}
}
