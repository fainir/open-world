import * as THREE from 'three';
export default class CoffeeShop{
  constructor(api){this.api=api;this.group=null}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=12,D=10,H=3.5;
    const wallM=new THREE.MeshStandardMaterial({color:0xf5e6c8,roughness:.8,side:THREE.DoubleSide});
    // Floor
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0x8B6914,roughness:.9}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xeee8d5,roughness:.9,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    const bw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);bw.position.set(0,H/2,-D/2);group.add(bw);
    const fw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);fw.position.set(0,H/2,D/2);group.add(fw);
    for(const s of[-1,1]){const sw=new THREE.Mesh(new THREE.PlaneGeometry(D,H),wallM);sw.rotation.y=s*Math.PI/2;sw.position.set(s*W/2,H/2,0);group.add(sw)}
    // Counter
    const counter=box(5,1.1,.8,0x5c3a1a);counter.position.set(-1.5,.55,-3.5);group.add(counter);
    // Counter top
    const ctop=box(5.2,.05,.9,0x8B6914);ctop.position.set(-1.5,1.12,-3.5);group.add(ctop);
    // Espresso machine
    const machine=box(.7,.6,.5,0x888888);machine.position.set(-3,1.4,-3.5);group.add(machine);
    // Coffee cups on counter
    for(let i=0;i<3;i++){const cup=new THREE.Mesh(new THREE.CylinderGeometry(.05,.04,.12,6),new THREE.MeshStandardMaterial({color:0xffffff}));
      cup.position.set(-1+i*.8,1.18,-3.5);group.add(cup)}
    // Menu board behind counter
    const menu=box(3,1.5,.05,0x222222);menu.position.set(-1.5,2.5,-4.9);group.add(menu);
    // Tables (4)
    for(let i=0;i<4;i++){const tx=-3+i*2.2,tz=i<2?1:3;
      const tbl=box(1,.05,1,0x6a4a2a);tbl.position.set(tx,.75,tz);group.add(tbl);
      const leg=cyl(.03,.03,.75,0x444444);leg.position.set(tx,.375,tz);group.add(leg);
      for(const cx of[-.45,.45])for(const cz of[-.35,.35]){
        const chair=box(.4,.02,.4,0x8B4513);chair.position.set(tx+cx,.45,tz+cz);group.add(chair);
        const cleg=cyl(.02,.02,.45,0x555555);cleg.position.set(tx+cx,.225,tz+cz);group.add(cleg);
        const cback=box(.4,.3,.03,0x8B4513);cback.position.set(tx+cx,.7,tz+cz+(cz>0?.18:-.18));group.add(cback)}}
    // Pastry display case
    const display=box(1,.6,.6,0xffffff);display.material=new THREE.MeshStandardMaterial({color:0xeeffff,transparent:true,opacity:.4});
    display.position.set(1.5,.9,-3.5);group.add(display);
    // Bookshelf on side wall
    const shelf=box(.2,2.5,1.5,0x6a4a2a);shelf.position.set(5.8,1.25,-2);group.add(shelf);
    for(let i=0;i<4;i++){const shb=box(.18,.02,1.4,0x6a4a2a);shb.position.set(5.8,.5+i*.6,-2);group.add(shb)}
    // Lights
    group.add(new THREE.AmbientLight(0xffeedd,.7));
    const spot=new THREE.PointLight(0xffcc88,1.5,15);spot.position.set(0,3.2,0);group.add(spot);
    const spot2=new THREE.PointLight(0xffcc88,.8,10);spot2.position.set(-2,3.2,-3);group.add(spot2);
    // Plants
    for(const[px,pz] of[[5.5,4],[- 5.5,4]]){
      const pot=cyl(.2,.25,.3,0x884422);pot.position.set(px,.15,pz);group.add(pot);
      const plant=new THREE.Mesh(new THREE.SphereGeometry(.3,6,5),new THREE.MeshStandardMaterial({color:0x228833}));
      plant.position.set(px,.5,pz);group.add(plant)}
    // Player position
    const gp=group.position;
    this.api.P.set(gp.x,gp.y+1.7,gp.z+3);
    this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
  }
  update(dt){
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    const spd=5,f=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),r=new THREE.Vector3(f.z,0,-f.x);
    if(keys['KeyW']||keys['ArrowUp']){P.x+=f.x*spd*dt;P.z+=f.z*spd*dt}
    if(keys['KeyS']||keys['ArrowDown']){P.x-=f.x*spd*dt;P.z-=f.z*spd*dt}
    if(keys['KeyA']||keys['ArrowLeft']){P.x-=r.x*spd*dt;P.z-=r.z*spd*dt}
    if(keys['KeyD']||keys['ArrowRight']){P.x+=r.x*spd*dt;P.z+=r.z*spd*dt}
    const gp=this.group.position;
    P.x=this.api.clamp(P.x,gp.x-5.5,gp.x+5.5);P.z=this.api.clamp(P.z,gp.z-4.5,gp.z+4.5);
    P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
  }
  async exit(){}
}
