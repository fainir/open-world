import * as THREE from 'three';
export default class ConvenienceStore{
  constructor(api){this.api=api;this.group=null}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=10,D=8,H=3;
    const wallM=new THREE.MeshStandardMaterial({color:0xf5f5f0,roughness:.7,side:THREE.DoubleSide});
    // Floor (linoleum)
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xddddcc,roughness:.4}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xeeeeee,roughness:.7,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    const bw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);bw.position.set(0,H/2,-D/2);group.add(bw);
    const fw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);fw.position.set(0,H/2,D/2);group.add(fw);
    for(const s of[-1,1]){const sw=new THREE.Mesh(new THREE.PlaneGeometry(D,H),wallM);sw.rotation.y=s*Math.PI/2;sw.position.set(s*W/2,H/2,0);group.add(sw)}
    // Shelving aisles (3 rows)
    const prodC=[0xff4444,0x44ff44,0x4444ff,0xffff44,0xff44ff,0x44ffff,0xff8844,0x8844ff];
    for(let r=0;r<3;r++){const rx=-2.5+r*2.5;
      const shelf=box(.2,1.8,5,0xccccbb);shelf.position.set(rx,.9,-1);group.add(shelf);
      // Products on shelves (3 shelf levels)
      for(let lv=0;lv<3;lv++){
        const shelfB=box(.18,.03,4.8,0xccccbb);shelfB.position.set(rx,.4+lv*.6,-1);group.add(shelfB);
        for(let p=0;p<8;p++){
          const prod=box(.12,.15,.1,prodC[(r*8+lv*3+p)%8]);
          prod.position.set(rx,.52+lv*.6,-3.2+p*.65);group.add(prod)}}}
    // Refrigerators along back wall
    for(let i=0;i<3;i++){
      const fridge=box(1.5,2.2,.8,0xdddddd);fridge.position.set(-3+i*2.5,1.1,-3.5);group.add(fridge);
      const glass=new THREE.Mesh(new THREE.PlaneGeometry(1.3,1.8),new THREE.MeshStandardMaterial({color:0xccddee,transparent:true,opacity:.3}));
      glass.position.set(-3+i*2.5,1.2,-3.08);group.add(glass);
      // Drinks inside
      for(let d=0;d<4;d++){const drink=cyl(.03,.03,.2,[0xff0000,0x00aa00,0x0044ff,0xffaa00][d]);
        drink.position.set(-3.3+i*2.5+d*.2,1,-3.5);group.add(drink)}}
    // Checkout counter
    const counter=box(2.5,.9,.6,0xaaaaaa);counter.position.set(3.5,.45,2.5);group.add(counter);
    const reg=box(.4,.3,.25,0x333333);reg.position.set(3.5,1.05,2.5);group.add(reg);
    // Snack display near counter
    const snack=box(.8,1.2,.4,0xdddddd);snack.position.set(2,.6,2.5);group.add(snack);
    for(let i=0;i<6;i++){const s=box(.15,.08,.08,prodC[i]);s.position.set(2-.2+Math.floor(i/3)*.25,.4+i%3*.25,2.5);group.add(s)}
    // Slurpee machine
    const slurp=box(.6,.8,.4,0xdddddd);slurp.position.set(4.2,.9,2);group.add(slurp);
    for(const c of[0xff0000,0x0000ff,0x00ff00]){const tap=cyl(.03,.03,.1,c);tap.position.set(4+c/0x1000000*.3,1.35,1.8);group.add(tap)}
    // Bright fluorescent lighting
    group.add(new THREE.AmbientLight(0xffffff,.9));
    const fl=new THREE.PointLight(0xffffff,1,12);fl.position.set(0,2.8,0);group.add(fl);
    // Position
    const gp=group.position;
    this.api.P.set(gp.x,gp.y+1.7,gp.z+2.5);this.api.V.set(0,0,0);this.api.yaw=Math.PI;this.api.pitch=0;this.api.mode='walk';
  }
  update(dt){
    const{P,cam,keys}=this.api;const yaw=this.api.yaw,pitch=this.api.pitch;
    const spd=5,f=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),r=new THREE.Vector3(f.z,0,-f.x);
    if(keys['KeyW']||keys['ArrowUp']){P.x+=f.x*spd*dt;P.z+=f.z*spd*dt}
    if(keys['KeyS']||keys['ArrowDown']){P.x-=f.x*spd*dt;P.z-=f.z*spd*dt}
    if(keys['KeyA']||keys['ArrowLeft']){P.x-=r.x*spd*dt;P.z-=r.z*spd*dt}
    if(keys['KeyD']||keys['ArrowRight']){P.x+=r.x*spd*dt;P.z+=r.z*spd*dt}
    const gp=this.group.position;
    P.x=this.api.clamp(P.x,gp.x-4.5,gp.x+4.5);P.z=this.api.clamp(P.z,gp.z-3.5,gp.z+3.5);P.y=gp.y+1.7;
    cam.position.set(P.x,P.y,P.z);cam.rotation.set(pitch,yaw,0,'YXZ');
  }
  async exit(){}
}
