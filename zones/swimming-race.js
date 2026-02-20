import * as THREE from 'three';
export default class SwimmingRace{
  constructor(api){this.api=api;this.group=null;this.state='ready';this.playerLane=3;
    this.playerDist=0;this.oppDists=[];this.hudEl=null;this.poolLen=50;
    this.mashCount=0;this.mashDecay=0;this.speed=0;this.countdown=3;this.raceTime=0}
  async enter(group,zone){
    this.group=group;this.state='ready';this.playerDist=0;this.speed=0;this.countdown=3;this.raceTime=0;
    this.mashCount=0;this.mashDecay=0;
    this.oppDists=[0,0,0,0,0,0,0];this.oppSpeeds=Array(7).fill(0);
    const{box,cyl}=this.api;
    // Pool
    const poolFloor=new THREE.Mesh(new THREE.PlaneGeometry(25,50),new THREE.MeshStandardMaterial({color:0x1166aa,roughness:.2}));
    poolFloor.rotation.x=-Math.PI/2;poolFloor.position.y=-.5;group.add(poolFloor);
    const water=new THREE.Mesh(new THREE.PlaneGeometry(25,50),new THREE.MeshStandardMaterial({color:0x44aaee,transparent:true,opacity:.5,roughness:.1}));
    water.rotation.x=-Math.PI/2;water.add(water);group.add(water);
    // Deck
    const deckM=new THREE.MeshStandardMaterial({color:0xccccbb,roughness:.6});
    for(const dz of[-26,26]){const d=new THREE.Mesh(new THREE.PlaneGeometry(29,3),deckM);d.rotation.x=-Math.PI/2;d.position.set(0,.08,dz);group.add(d)}
    for(const dx of[-14,14]){const d=new THREE.Mesh(new THREE.PlaneGeometry(3,54),deckM);d.rotation.x=-Math.PI/2;d.position.set(dx,.08,0);group.add(d)}
    // Lane lines (8 lanes)
    const lnM=new THREE.MeshStandardMaterial({color:0xffdd00,transparent:true,opacity:.5});
    for(let ln=0;ln<=8;ln++){const lx=-12.5+ln*(25/8);
      const lane=new THREE.Mesh(new THREE.PlaneGeometry(.1,48),lnM);lane.rotation.x=-Math.PI/2;lane.position.set(lx,.02,0);group.add(lane)}
    // Starting blocks
    for(let sb=0;sb<8;sb++){const sbx=-12.5+sb*(25/8)+25/16;
      const block=box(.6,.4,.8,0xdddddd);block.position.set(sbx,.2,-24);group.add(block)}
    // Swimmer markers (player + 7 opponents)
    this.swimmers=[];
    for(let i=0;i<8;i++){const lx=-12.5+i*(25/8)+25/16;
      const swimmer=new THREE.Mesh(new THREE.SphereGeometry(.2,6,5),
        new THREE.MeshStandardMaterial({color:i===this.playerLane?0x44ff44:0xff4444}));
      swimmer.position.set(lx,0,-23);group.add(swimmer);this.swimmers.push(swimmer)}
    // Lighting
    group.add(new THREE.AmbientLight(0xffffff,.8));
    const sun=new THREE.DirectionalLight(0xffffff,.6);sun.position.set(5,10,5);group.add(sun);
    // HUD
    this.hudEl=document.createElement('div');this.hudEl.id='mission-hud';
    this.hudEl.style.cssText='position:fixed;top:20px;left:50%;transform:translateX(-50%);color:#fff;font-family:"Courier New",monospace;font-size:1.3em;background:rgba(0,0,0,0.6);padding:8px 20px;border-radius:8px;z-index:7';
    document.body.appendChild(this.hudEl);
    // Speed bar
    this.speedEl=document.createElement('div');this.speedEl.style.cssText='position:fixed;bottom:80px;left:50%;transform:translateX(-50%);width:200px;height:8px;background:rgba(255,255,255,0.2);border-radius:4px;z-index:7';
    const fill=document.createElement('div');fill.style.cssText='width:0%;height:100%;background:linear-gradient(90deg,#44ff44,#ffaa00);border-radius:4px';
    this.speedEl.appendChild(fill);this.speedFill=fill;
    document.body.appendChild(this.speedEl);
    this.api.P.set(group.position.x,group.position.y+10,group.position.z+15);
    this.api.V.set(0,0,0);this.api.mode='walk';
    this._updateHUD();
    this.api.showTip('Swimming Race! Mash SPACE or click to swim! Get ready...');
  }
  _updateHUD(){
    if(!this.hudEl)return;
    if(this.state==='ready')this.hudEl.textContent=`GET READY... ${Math.ceil(this.countdown)}`;
    else if(this.state==='racing'){const pct=(this.playerDist/this.poolLen*100)|0;
      this.hudEl.textContent=`${pct}% | Time: ${this.raceTime.toFixed(1)}s`}
    else this.hudEl.textContent=this.state==='won'?`WIN! Time: ${this.raceTime.toFixed(1)}s`:`Finished ${this.getPlace()}`}
  getPlace(){let place=1;for(const d of this.oppDists)if(d>this.playerDist)place++;
    return place<=1?'1st!':place===2?'2nd':place===3?'3rd':place+'th'}
  update(dt){
    const gp=this.group.position;
    if(this.state==='ready'){
      this.countdown-=dt;
      if(this.countdown<=0){this.state='racing';this.api.showTip('GO! Mash SPACE!')}
      this._updateHUD();
      const cam=this.api.cam;cam.position.set(gp.x,gp.y+12,gp.z);cam.lookAt(gp.x,gp.y,gp.z);return}
    if(this.state==='done'||this.state==='won'){
      const cam=this.api.cam;cam.position.set(gp.x,gp.y+12,gp.z);cam.lookAt(gp.x,gp.y,gp.z);return}
    this.raceTime+=dt;
    // Mash detection
    this.mashDecay=Math.max(0,this.mashDecay-dt*3);
    if(this.api.keys['Space']||this.api.keys['mouse0']||this.api.keys['_shooting']){
      this.api.keys['Space']=false;this.api.keys['mouse0']=false;this.api.keys['_shooting']=false;
      this.mashCount++;this.mashDecay=1}
    this.speed=this.mashDecay*12;
    this.playerDist+=this.speed*dt;
    this.speedFill.style.width=Math.min(100,this.speed/12*100)+'%';
    // Update player swimmer position
    const pSwim=this.swimmers[this.playerLane];
    pSwim.position.z=-23+this.playerDist;
    // Opponent AI
    for(let i=0;i<7;i++){const li=i>=this.playerLane?i+1:i;
      const target=6+Math.random()*4+i*.5;
      this.oppSpeeds[i]+=(target-this.oppSpeeds[i])*(1+Math.random())*dt;
      this.oppDists[i]+=this.oppSpeeds[i]*dt;
      this.swimmers[li].position.z=-23+this.oppDists[i]}
    // Check finish
    if(this.playerDist>=this.poolLen){
      let won=true;for(const d of this.oppDists)if(d>=this.poolLen)won=false;
      this.state=won?'won':'done';
      this.api.showTip(won?'You WON! +500 pts':`Race over! You finished ${this.getPlace()}`)}
    this._updateHUD();
    // Camera follows race
    const cam=this.api.cam;
    cam.position.set(gp.x+15,gp.y+8,gp.z-23+this.playerDist);
    cam.lookAt(gp.x,gp.y,gp.z-23+this.playerDist);
  }
  async exit(){if(this.hudEl){this.hudEl.remove();this.hudEl=null}
    if(this.speedEl){this.speedEl.remove();this.speedEl=null}this.swimmers=[]}
}
