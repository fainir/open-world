import * as THREE from 'three';
export default class ClothingStore{
  constructor(api){this.api=api;this.group=null}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=14,D=12,H=4;
    const wallM=new THREE.MeshStandardMaterial({color:0xf0f0f0,roughness:.7,side:THREE.DoubleSide});
    // Floor (polished)
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xe8e0d8,roughness:.3,metalness:.1}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xffffff,roughness:.7,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    const bw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);bw.position.set(0,H/2,-D/2);group.add(bw);
    const fw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);fw.position.set(0,H/2,D/2);group.add(fw);
    for(const s of[-1,1]){const sw=new THREE.Mesh(new THREE.PlaneGeometry(D,H),wallM);sw.rotation.y=s*Math.PI/2;sw.position.set(s*W/2,H/2,0);group.add(sw)}
    // Clothing racks (4 rows)
    const rackC=[0xdd4466,0x4488dd,0x44bb66,0xddaa44,0xaa44dd,0x44dddd];
    for(let r=0;r<4;r++){const rx=-4+r*3,rz=-2;
      const pole=cyl(.02,.02,1.8,0xcccccc);pole.position.set(rx,.9,rz);group.add(pole);
      const bar2=cyl(.015,.015,2,0xcccccc);bar2.rotation.z=Math.PI/2;bar2.position.set(rx,1.8,rz);group.add(bar2);
      // Hanging clothes
      for(let c=0;c<5;c++){const hanger=box(.3,.5,.03,rackC[(r*5+c)%6]);hanger.position.set(rx-1+c*.5,1.4,rz);group.add(hanger)}}
    // Mannequins (3)
    const mannC=[0xeeeeee,0x222222,0xcc8844];
    for(let m=0;m<3;m++){const mx=-3+m*3,mz=3;
      // Body
      const body=cyl(.2,.15,1,mannC[m]);body.position.set(mx,1.2,mz);group.add(body);
      // Head
      const head=new THREE.Mesh(new THREE.SphereGeometry(.12,8,6),new THREE.MeshStandardMaterial({color:0xddccbb}));
      head.position.set(mx,1.85,mz);group.add(head);
      // Base
      const base=cyl(.25,.3,.1,0x333333);base.position.set(mx,.05,mz);group.add(base)}
    // Checkout counter
    const counter=box(3,.9,.7,0xffffff);counter.position.set(5,.45,-4);group.add(counter);
    // Cash register
    const reg=box(.4,.3,.3,0x333333);reg.position.set(5,1.05,-4);group.add(reg);
    // Shoe display wall
    for(let r=0;r<3;r++)for(let c=0;c<4;c++){
      const shelf=box(1.2,.05,.4,0xeeeeee);shelf.position.set(-6.8,.5+r*.8,-3+c*1.5);shelf.rotation.y=Math.PI/2;group.add(shelf);
      const shoe=box(.25,.1,.08,[0x222222,0xcc4444,0x4444cc,0xffffff][(r+c)%4]);
      shoe.position.set(-6.8,.6+r*.8,-3+c*1.5);shoe.rotation.y=Math.PI/2;group.add(shoe)}
    // Fitting rooms (2 curtains)
    for(let i=0;i<2;i++){const fx=3+i*2.5,fz=-4;
      const curtain=new THREE.Mesh(new THREE.PlaneGeometry(1.5,2.5),new THREE.MeshStandardMaterial({color:0x8866aa,side:THREE.DoubleSide}));
      curtain.position.set(fx,1.5,fz);group.add(curtain);
      const rod=cyl(.015,.015,1.6,0xcccccc);rod.rotation.z=Math.PI/2;rod.position.set(fx,2.8,fz);group.add(rod)}
    // Full length mirror
    const mirr=new THREE.Mesh(new THREE.PlaneGeometry(1,2.5),new THREE.MeshStandardMaterial({color:0xaaccee,metalness:.9,roughness:.05}));
    mirr.position.set(6.9,1.5,0);mirr.rotation.y=-Math.PI/2;group.add(mirr);
    // Bright lighting
    group.add(new THREE.AmbientLight(0xffffff,.8));
    const spot=new THREE.PointLight(0xffffff,1,15);spot.position.set(0,3.8,0);group.add(spot);
    const spot2=new THREE.PointLight(0xffeedd,.6,10);spot2.position.set(-3,3.8,3);group.add(spot2);
    // Position
    const gp=group.position;
    this.api.P.set(gp.x,gp.y+1.7,gp.z+4);this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
  }
  update(dt){
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    const spd=5,f=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),r=new THREE.Vector3(f.z,0,-f.x);
    if(keys['KeyW']||keys['ArrowUp']){P.x+=f.x*spd*dt;P.z+=f.z*spd*dt}
    if(keys['KeyS']||keys['ArrowDown']){P.x-=f.x*spd*dt;P.z-=f.z*spd*dt}
    if(keys['KeyA']||keys['ArrowLeft']){P.x-=r.x*spd*dt;P.z-=r.z*spd*dt}
    if(keys['KeyD']||keys['ArrowRight']){P.x+=r.x*spd*dt;P.z+=r.z*spd*dt}
    const gp=this.group.position;
    P.x=this.api.clamp(P.x,gp.x-6.5,gp.x+6.5);P.z=this.api.clamp(P.z,gp.z-5.5,gp.z+5.5);P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
  }
  async exit(){}
}
