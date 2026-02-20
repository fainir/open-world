import * as THREE from 'three';
export default class RestaurantInterior{
  constructor(api){this.api=api;this.group=null}
  async enter(group,zone){
    this.group=group;
    const{box,cyl}=this.api;
    const W=14,D=12,H=3.5;
    const wallM=new THREE.MeshStandardMaterial({color:0xeeddcc,roughness:.8,side:THREE.DoubleSide});
    // Floor (tiles)
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xaa8866,roughness:.6}));
    floor.rotation.x=-Math.PI/2;group.add(floor);
    // Ceiling
    const ceil=new THREE.Mesh(new THREE.PlaneGeometry(W,D),new THREE.MeshStandardMaterial({color:0xf5eedf,roughness:.8,side:THREE.DoubleSide}));
    ceil.rotation.x=Math.PI/2;ceil.position.y=H;group.add(ceil);
    // Walls
    const bw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);bw.position.set(0,H/2,-D/2);group.add(bw);
    const fw=new THREE.Mesh(new THREE.PlaneGeometry(W,H),wallM);fw.position.set(0,H/2,D/2);group.add(fw);
    for(const s of[-1,1]){const sw=new THREE.Mesh(new THREE.PlaneGeometry(D,H),wallM);sw.rotation.y=s*Math.PI/2;sw.position.set(s*W/2,H/2,0);group.add(sw)}
    // Dining tables (6) with tablecloths
    const clothC=[0xcc2222,0x2222cc,0xffffff,0x22cc22,0xcc8822,0xcc22cc];
    for(let i=0;i<6;i++){const tx=-4+(i%3)*4,tz=i<3?-2:2;
      // Table
      const tbl=box(1.5,.05,1.2,0x6a4a2a);tbl.position.set(tx,.75,tz);group.add(tbl);
      const leg=cyl(.04,.04,.75,0x444444);leg.position.set(tx,.375,tz);group.add(leg);
      // Tablecloth (slightly larger, draped)
      const cloth=box(1.6,.02,1.3,clothC[i]);cloth.position.set(tx,.77,tz);group.add(cloth);
      // Plates
      for(const dx of[-.35,.35]){const plate=cyl(.12,.12,.01,0xffffff);plate.position.set(tx+dx,.79,tz);group.add(plate)}
      // Wine glass
      const glass=cyl(.03,.02,.1,0xeeffee);glass.material=new THREE.MeshStandardMaterial({color:0xeeffee,transparent:true,opacity:.3});
      glass.position.set(tx+.35,.84,tz-.2);group.add(glass);
      // Chairs (2)
      for(const cz of[-.8,.8]){
        const chair=box(.4,.02,.4,0x6a4a2a);chair.position.set(tx,.45,tz+cz);group.add(chair);
        const cback=box(.4,.5,.04,0x6a4a2a);cback.position.set(tx,.7,tz+cz+(cz>0?.2:-.2));group.add(cback)}}
    // Kitchen area (behind wall partition)
    const partition=box(W*.8,2.5,.1,0xeeddcc);partition.position.set(0,1.25,-4.5);group.add(partition);
    const passWindow=box(3,1,.05,0x333333);passWindow.position.set(0,2,-4.5);group.add(passWindow);
    // Kitchen equipment behind partition
    const stove=box(1.5,.9,.8,0x888888);stove.position.set(-2,.45,-5.5);group.add(stove);
    const oven=box(1,.8,.7,0x555555);oven.position.set(1,.4,-5.5);group.add(oven);
    // Wine rack
    const rack=box(.3,2.5,1,0x6a4a2a);rack.position.set(6.8,1.25,0);group.add(rack);
    for(let r=0;r<4;r++)for(let c=0;c<3;c++){
      const wine=cyl(.03,.03,.25,r%2===0?0x440000:0x004400);wine.rotation.z=Math.PI/2;
      wine.position.set(6.8,.4+r*.5,-.3+c*.3);group.add(wine)}
    // Paintings on wall
    for(let i=0;i<3;i++){const paint=box(1.2,.8,.03,[0xcc6644,0x4466cc,0x66cc44][i]);
      paint.position.set(-4+i*4,2.2,5.95);group.add(paint);
      const frame=box(1.4,1,.04,0x6a4a2a);frame.position.set(-4+i*4,2.2,5.97);group.add(frame)}
    // Candle centerpieces
    for(let i=0;i<6;i++){const tx=-4+(i%3)*4,tz=i<3?-2:2;
      const candle=cyl(.02,.02,.1,0xffeecc);candle.position.set(tx,.84,tz);group.add(candle);
      const flame=new THREE.Mesh(new THREE.ConeGeometry(.015,.04,4),
        new THREE.MeshStandardMaterial({color:0xff8800,emissive:0xff6600,emissiveIntensity:2}));
      flame.position.set(tx,.9,tz);group.add(flame)}
    // Warm lighting
    group.add(new THREE.AmbientLight(0xffeedd,.5));
    const pl=new THREE.PointLight(0xffcc88,1,12);pl.position.set(0,3.2,0);group.add(pl);
    const pl2=new THREE.PointLight(0xffaa66,.5,8);pl2.position.set(-4,3.2,-2);group.add(pl2);
    const pl3=new THREE.PointLight(0xffaa66,.5,8);pl3.position.set(4,3.2,2);group.add(pl3);
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
