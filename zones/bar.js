import * as THREE from 'three';
export default class Bar{
  constructor(api){this.api=api;this.group=null;this.t=0}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=14,D=10,H=3.5;
    const wallM=new THREE.MeshStandardMaterial({color:0x2a1a0a,roughness:.9,side:THREE.DoubleSide});
    // Floor (dark wood)
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0x3a2a1a,roughness:.85}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0x1a1a1a,roughness:.9,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    const bw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);bw.position.set(0,H/2,-D/2);group.add(bw);
    const fw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);fw.position.set(0,H/2,D/2);group.add(fw);
    for(const s of[-1,1]){const sw=new THREE.Mesh(new THREE.PlaneGeometry(D,H),wallM);sw.rotation.y=s*Math.PI/2;sw.position.set(s*W/2,H/2,0);group.add(sw)}
    // Long bar counter
    const bar=box(8,1.1,.9,0x4a2a0a);bar.position.set(0,.55,-3.5);group.add(bar);
    const btop=box(8.2,.06,1,0x6a4a2a);btop.position.set(0,1.12,-3.5);group.add(btop);
    // Bar stools (6)
    for(let i=0;i<6;i++){const sx=-3+i*1.3;
      const stool=cyl(.15,.18,.7,0x333333);stool.position.set(sx,.35,-2.5);group.add(stool);
      const seat=cyl(.2,.2,.05,0x8B4513);seat.position.set(sx,.72,-2.5);group.add(seat)}
    // Bottle shelf behind bar
    const shelf=box(7,.1,.4,0x4a2a0a);shelf.position.set(0,2,-4.7);group.add(shelf);
    const shelf2=box(7,.1,.4,0x4a2a0a);shelf2.position.set(0,2.8,-4.7);group.add(shelf2);
    // Bottles
    const bottleC=[0x228833,0x882222,0xaa8822,0x224488,0x882288,0xcc8833];
    for(let i=0;i<10;i++){const bx=-3+i*.7;
      const bottle=cyl(.04,.04,.25,bottleC[i%6]);bottle.position.set(bx,2.22,-4.7);group.add(bottle)}
    for(let i=0;i<8;i++){const bx=-2.5+i*.7;
      const bottle=cyl(.04,.04,.25,bottleC[(i+3)%6]);bottle.position.set(bx,3,-4.7);group.add(bottle)}
    // Mirror behind bar
    const mirror=new THREE.Mesh(new THREE.PlaneGeometry(5,1.5),new THREE.MeshStandardMaterial({color:0x88aacc,metalness:.9,roughness:.05}));
    mirror.position.set(0,2.4,-4.95);group.add(mirror);
    // Neon signs
    const neonM=c=>new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:1.5});
    const neon1=box(2,.4,.05,0xff0066);neon1.material=neonM(0xff0066);neon1.position.set(-5,2.5,-4.9);group.add(neon1);
    const neon2=box(1.5,.3,.05,0x00aaff);neon2.material=neonM(0x00aaff);neon2.position.set(5,2.5,-4.9);group.add(neon2);
    // Tables (3 round)
    for(let i=0;i<3;i++){const tx=-3+i*3,tz=2;
      const tbl=cyl(.5,.5,.05,0x4a2a0a);tbl.position.set(tx,.75,tz);group.add(tbl);
      const tleg=cyl(.04,.04,.75,0x333333);tleg.position.set(tx,.375,tz);group.add(tleg)}
    // Pool table
    const pool=box(2.5,.85,1.4,0x226622);pool.position.set(4,.425,1);group.add(pool);
    const felt=new THREE.Mesh(new THREE.PlaneGeometry(2.3,1.2),new THREE.MeshStandardMaterial({color:0x006622}));
    felt.rotation.x=-Math.PI/2;felt.position.set(4,.86,1);group.add(felt);
    // Dart board on wall
    const dart=new THREE.Mesh(new THREE.CircleGeometry(.4,16),new THREE.MeshStandardMaterial({color:0xcc3333}));
    dart.position.set(6.9,1.8,0);dart.rotation.y=-Math.PI/2;group.add(dart);
    const dInner=new THREE.Mesh(new THREE.CircleGeometry(.15,12),new THREE.MeshStandardMaterial({color:0x228822}));
    dInner.position.set(6.89,1.8,0);dInner.rotation.y=-Math.PI/2;group.add(dInner);
    // Lighting (dim, moody)
    group.add(new THREE.AmbientLight(0x442211,.4));
    const pl1=new THREE.PointLight(0xff8844,.8,10);pl1.position.set(0,3,-3);group.add(pl1);
    const pl2=new THREE.PointLight(0xffaa66,.6,8);pl2.position.set(4,2.5,1);group.add(pl2);
    this.neonLight=new THREE.PointLight(0xff0066,.5,6);this.neonLight.position.set(-5,2.5,-4);group.add(this.neonLight);
    // Position
    const gp=group.position;
    this.api.P.set(gp.x,gp.y+1.7,gp.z+3);this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
  }
  update(dt){
    this.t+=dt;
    if(this.neonLight)this.neonLight.intensity=.3+Math.sin(this.t*2)*.2;
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    const spd=5,f=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),r=new THREE.Vector3(f.z,0,-f.x);
    if(keys['KeyW']||keys['ArrowUp']){P.x+=f.x*spd*dt;P.z+=f.z*spd*dt}
    if(keys['KeyS']||keys['ArrowDown']){P.x-=f.x*spd*dt;P.z-=f.z*spd*dt}
    if(keys['KeyA']||keys['ArrowLeft']){P.x-=r.x*spd*dt;P.z-=r.z*spd*dt}
    if(keys['KeyD']||keys['ArrowRight']){P.x+=r.x*spd*dt;P.z+=r.z*spd*dt}
    const gp=this.group.position;
    P.x=this.api.clamp(P.x,gp.x-6.5,gp.x+6.5);P.z=this.api.clamp(P.z,gp.z-4.5,gp.z+4.5);P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
  }
  async exit(){this.neonLight=null}
}
