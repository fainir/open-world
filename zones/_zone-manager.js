// Zone Manager — proximity detection, lazy loading, enter/exit orchestration
import * as THREE from 'three';

export class ZoneManager {
  constructor(api){
    this.api=api;
    this.zones=[];
    this.activeZone=null;
    this.loadedModules={};    // id -> module instance (cached)
    this.nearestZone=null;
    this.interiorGroup=null;
    this.savedState=null;
    this.transitioning=false;
    this.eJust=false;
    this._ePressed=false;

    // E key handler (mirrors fJust pattern)
    document.addEventListener('keydown',e=>{
      if(e.code==='KeyE'&&!this._ePressed){this._ePressed=true;this.eJust=true}
    });
    document.addEventListener('keyup',e=>{
      if(e.code==='KeyE')this._ePressed=false;
    });
  }

  init(zoneDefs){
    for(const def of zoneDefs){
      this.zones.push({...def,loaded:false,moduleInstance:null});
    }
  }

  // Called every frame from the main update()
  update(dt){
    if(this.transitioning)return;

    // If inside a zone, delegate to module
    if(this.activeZone){
      const mod=this.loadedModules[this.activeZone.id];
      if(mod&&mod.update)mod.update(dt);
      // E to exit
      if(this.eJust){this.eJust=false;this.exitZone()}
      this.eJust=false;
      return;
    }

    // Proximity detection
    this.nearestZone=null;
    let bestDist=Infinity;
    const P=this.api.P;
    for(const z of this.zones){
      const dx=P.x-z.position[0],dz=P.z-z.position[2];
      const dist=Math.sqrt(dx*dx+dz*dz);
      if(dist<z.radius&&dist<bestDist){bestDist=dist;this.nearestZone=z}
    }

    // E to enter
    if(this.eJust&&this.nearestZone){this.eJust=false;this.enterZone(this.nearestZone)}
    this.eJust=false;
  }

  async enterZone(zone){
    if(this.transitioning||this.activeZone)return;
    this.transitioning=true;
    const api=this.api;

    // Save player state
    this.savedState={
      position:api.P.clone(),velocity:api.V.clone(),
      yaw:api.yaw,pitch:api.pitch,mode:api.mode,
      isFlying:api.isFlying,currentVeh:api.currentVeh,
      charVisible:api.charG.visible,camFov:api.cam.fov
    };

    // Dismount if in vehicle
    if(api.currentVeh)api.dismountVehicle();

    // Fade to black
    await api.ui.fadeOut(400);
    api.ui.hidePrompt();

    // Lazy-load module
    if(!this.loadedModules[zone.id]){
      try{
        const mod=await import(zone.module);
        this.loadedModules[zone.id]=new mod.default(api);
      }catch(err){
        console.error('Zone load failed:',zone.id,err);
        api.showTip('Failed to load '+zone.label);
        await api.ui.fadeIn(400);
        this.transitioning=false;
        return;
      }
    }

    const mod=this.loadedModules[zone.id];

    // Create interior group at pocket dimension y=-500
    this.interiorGroup=new THREE.Group();
    this.interiorGroup.name='zone-'+zone.id;
    this.interiorGroup.position.set(0,-500,0);
    api.scene.add(this.interiorGroup);

    // Hide character
    api.charG.visible=false;

    // Module builds interior
    await mod.enter(this.interiorGroup,zone);

    this.activeZone=zone;
    api.showTip(zone.label+' — Press E to leave');
    await api.ui.fadeIn(400);
    this.transitioning=false;
  }

  async exitZone(){
    if(this.transitioning||!this.activeZone)return;
    this.transitioning=true;
    const api=this.api;
    const mod=this.loadedModules[this.activeZone.id];

    await api.ui.fadeOut(400);

    // Module cleanup
    if(mod&&mod.exit)await mod.exit();

    // Dispose interior geometry
    this._disposeGroup(this.interiorGroup);
    api.scene.remove(this.interiorGroup);
    this.interiorGroup=null;

    // Restore player state
    const s=this.savedState;
    api.P.copy(s.position);api.V.copy(s.velocity);
    api.yaw=s.yaw;api.pitch=s.pitch;
    api.mode=s.mode;api.isFlying=s.isFlying;
    api.charG.visible=true;
    api.cam.fov=s.camFov;api.cam.updateProjectionMatrix();

    this.activeZone=null;
    await api.ui.fadeIn(400);
    api.showTip('Back outside!');
    this.transitioning=false;

    try{api.canvas.requestPointerLock()}catch(e){}
  }

  _disposeGroup(group){
    group.traverse(obj=>{
      if(obj.geometry)obj.geometry.dispose();
      if(obj.material){
        if(Array.isArray(obj.material))obj.material.forEach(m=>{m.dispose();if(m.map)m.map.dispose()});
        else{obj.material.dispose();if(obj.material.map)obj.material.map.dispose()}
      }
    });
    while(group.children.length)group.remove(group.children[0]);
  }
}
