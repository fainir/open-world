import * as THREE from 'three';
export default class RaveInterior{
  constructor(api){this.api=api;this.group=null;this.t=0;this.tiles=[];this.strobes=[]}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=16,D=14,H=4;
    const wallM=new THREE.MeshStandardMaterial({color:0x0a0a15,roughness:.9,side:THREE.DoubleSide});
    const emM=c=>new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:1.5});
    // Floor (dark)
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0x111122,roughness:.3,metalness:.2}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0x0a0a0a,roughness:.9,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    for(const[rot,pos] of[[0,[0,H/2,-D/2]],[Math.PI,[0,H/2,D/2]],[Math.PI/2,[-W/2,H/2,0]],[-Math.PI/2,[W/2,H/2,0]]]){
      const w=new THREE.Mesh(new THREE.PlaneGeometry(rot===0||rot===Math.PI?W:D,H),wallM);
      w.rotation.y=rot;w.position.set(...pos);group.add(w)}
    // Dance floor tiles (colored, animated)
    const dfC=[0xff0066,0x6600ff,0x00ff66,0xff6600,0x0066ff,0xff00ff];
    for(let ix=-3;ix<=3;ix++)for(let iz=-3;iz<=3;iz++){
      const tc=dfC[(Math.abs(ix)+Math.abs(iz))%6];
      const tile=new THREE.Mesh(new THREE.PlaneGeometry(1.8,.05),
        new THREE.MeshStandardMaterial({color:tc,emissive:tc,emissiveIntensity:.3,roughness:.2}));
      tile.rotation.x=-Math.PI/2;tile.position.set(ix*2,.02,iz*2);group.add(tile);this.tiles.push(tile)}
    // DJ booth
    const djBooth=box(4,1.2,2,0x1a1a2a);djBooth.position.set(0,.6,-5.5);group.add(djBooth);
    const djTop=box(4.2,.05,2.2,0x222244);djTop.position.set(0,1.22,-5.5);group.add(djTop);
    // Turntables
    for(const dx of[-1,1]){const tt=cyl(.3,.3,.05,0x111111);tt.position.set(dx,1.28,-5.5);group.add(tt);
      const disc=cyl(.25,.25,.02,0x222222);disc.position.set(dx,1.31,-5.5);group.add(disc)}
    // Speaker stacks
    for(const sx of[-7,7])for(let h=0;h<3;h++){
      const spk=box(1.5,1.2,1.2,0x1a1a1a);spk.position.set(sx,.6+h*1.2,-5);group.add(spk)}
    // Neon strips on walls
    const neonC=[0xff00ff,0x00ffff,0xff0066,0x6600ff];
    for(let i=0;i<4;i++){const ny=1+i;
      const neon=new THREE.Mesh(new THREE.PlaneGeometry(W*.8,.1),emM(neonC[i]));
      neon.position.set(0,ny,-6.95);group.add(neon)}
    // Neon ring on ceiling
    const ring=new THREE.Mesh(new THREE.TorusGeometry(3,.06,6,24),emM(0xff00ff));
    ring.rotation.x=Math.PI/2;ring.position.set(0,3.9,0);group.add(ring);
    // Bar area (side)
    const bar=box(1,1,.4,0x2a1a2a);bar.position.set(7,.5,2);bar.rotation.y=Math.PI/2;group.add(bar);
    // Strobe lights
    for(const[sx,sz] of[[-4,3.8,-3],[4,3.8,-3],[0,3.8,3]]){
      const strobe=new THREE.PointLight(0xffffff,0,12);strobe.position.set(sx,sz,sz);group.add(strobe);this.strobes.push(strobe)}
    // Ambient (very dim)
    group.add(new THREE.AmbientLight(0x110022,.3));
    // Colored spots
    const spot1=new THREE.PointLight(0xff00ff,.8,10);spot1.position.set(0,3.8,0);group.add(spot1);
    const spot2=new THREE.PointLight(0x00aaff,.6,8);spot2.position.set(-4,3.8,-4);group.add(spot2);
    // Position
    const gp=group.position;
    this.api.P.set(gp.x,gp.y+1.7,gp.z+5);this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
  }
  update(dt){
    this.t+=dt;
    // Animate dance floor tiles
    for(let i=0;i<this.tiles.length;i++){
      const phase=this.t*3+i*.5;
      this.tiles[i].material.emissiveIntensity=.15+Math.sin(phase)*.35}
    // Strobe effect
    for(const s of this.strobes){s.intensity=Math.random()>.92?3:0}
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    const spd=5,f=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),r=new THREE.Vector3(f.z,0,-f.x);
    if(keys['KeyW']||keys['ArrowUp']){P.x+=f.x*spd*dt;P.z+=f.z*spd*dt}
    if(keys['KeyS']||keys['ArrowDown']){P.x-=f.x*spd*dt;P.z-=f.z*spd*dt}
    if(keys['KeyA']||keys['ArrowLeft']){P.x-=r.x*spd*dt;P.z-=r.z*spd*dt}
    if(keys['KeyD']||keys['ArrowRight']){P.x+=r.x*spd*dt;P.z+=r.z*spd*dt}
    const gp=this.group.position;
    P.x=this.api.clamp(P.x,gp.x-7.5,gp.x+7.5);P.z=this.api.clamp(P.z,gp.z-6.5,gp.z+6.5);P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
  }
  async exit(){this.tiles=[];this.strobes=[]}
}
