// Loaded inside the first-party city game module so the guide reads the same controls as play.
const cityPlayGuide = (() => {
  const activities = {
    'tennis-match': {hint:'Move to the ball and hit it back. First to five wins.', move:'Move', fire:'Hit'},
    'basketball-game': {hint:'Hold Shoot to build power. Release to take the shot.', move:'Move', fire:'Shoot'},
    'boxing-match': {hint:'Dodge, block the opponent, then punch when you have an opening.', move:'Dodge', fire:'Punch', boost:'Block'},
    'swimming-race': {hint:'Take a stroke when the breathing meter peaks.', action:'Stroke'},
    'archery-challenge': {hint:'Aim at the target, account for the wind, then release an arrow.', look:'Aim', fire:'Shoot'},
    'shooting-gallery': {hint:'Aim at the targets. Reload when the magazine is empty.', look:'Aim', fire:'Shoot', choices:[['KeyR','R','Reload']]},
    'bumper-cars': {hint:'Steer into other cars to score points.', move:'Drive'},
    'dance-challenge': {hint:'Follow the arrows in time. Hold a direction through a freeze arrow.', move:'Dance'},
    'go-kart-race': {hint:'Steer around the course and complete three laps.', move:'Drive'},
    'soccer-penalty': {hint:'Aim left or right. Hold Kick to charge and release to shoot.', move:'Aim', action:'Kick'},
    'obstacle-course': {hint:'Jump over the obstacles and try to beat the ghost.', move:'Move', action:'Jump'},
    'sprint-race': {hint:'Tap Sprint when the marker reaches the green zone.', action:'Sprint'},
    'high-dive': {hint:'Jump from the board. Flip in the air and straighten before the water.', action:'Jump / flip'},
    'ferris-wheel': {hint:'Photograph the glowing targets as they come into view.', action:'Photo'},
    'weight-lifting': {hint:'Lock in when the marker reaches the green zone.', action:'Lift'},
    'haunted-house': {hint:'Look around with your flashlight and find all eight scares.', move:'Walk', look:'Look'},
    'bowling-alley': {hint:'Aim left or right, then hold Bowl to charge. Steer during the roll for spin.', move:'Aim / spin', action:'Bowl'},
    'volleyball-match': {hint:'Move to meet the ball, then hit it over the net.', move:'Move', action:'Hit'},
    'halfpipe-challenge': {hint:'Move left or right. Use Trick at the lip of the ramp.', move:'Steer', action:'Trick'},
    'bungee-jump': {hint:'Jump from the platform. Time your next tap near the ground.', action:'Jump'},
    'parkour-race': {hint:'Jump between platforms and reach the gold one.', move:'Move', action:'Jump'},
    'wave-pool-surf': {hint:'Steer along the wave and do a trick at the peak.', move:'Steer', action:'Trick'},
    'slide-race': {hint:'Tap Speed up repeatedly to race down the slide.', action:'Speed up'},
    'diving-contest': {hint:'Jump from the board, then flip in the air.', action:'Jump / flip'},
    'coaster-ride': {hint:'Start the ride. Use the same button on drops to build excitement.', action:'Ride'},
    'teacup-spin': {hint:'Hold left or right to spin faster and earn points.', move:'Spin'},
    'haunted-walk': {hint:'Walk through the house. Scare ghosts back as they appear.', move:'Walk', action:'Scare'},
    'ferris-wheel-ride': {hint:'Take a photo when your seat reaches the top.', action:'Photo'},
  };
  const walk = {
    title:'Exploring',hint:'Approach an activity, door or vehicle to use it.', move:'Move', look:'Look',
    action:'Jump',boost:'Sprint',fire:'Shoot',use:'Enter',trick:'Tricks',fight:'Fight',menus:true,
  };
  const flying = {
    title:'Flying',hint:'Steer and tilt. Hold Rise to climb.', touchHint:'Use the stick to steer and tilt. Hold Rise to climb.',move:'Steer / tilt',
    action:'Rise',boost:'Boost',fire:'Shoot',use:'Enter',trick:'Tricks',menus:true,
  };
  const vehicles = {
    ground:{title:'Driving',hint:'Go forward to accelerate and back to brake or reverse.'},
    wearable:{title:'Riding',hint:'Steer through turns. Hop before trying a trick.'},
    snow:{title:'Snow sports',hint:'Stay on snow and steer downhill.'},
    water:{title:'Boating',hint:'Steer through open water. Back brakes or reverses.'},
    air:{title:'Flying a vehicle',hint:'Tilt up or down to change course. Hold Rise to climb.'},
  };
  const inside={hint:'Walk around the room. Use Leave to go back outside.',move:'Walk',look:'Look'};
  const boards={hint:'Choose a board height to get ready to dive.',choices:[
    ['Digit1','1','Low'],['Digit2','2','Medium'],['Digit3','3','High'],
  ]};
  const arcade={
    menu:{hint:'Choose a game to start playing.',choices:[['Digit1','1','Snake'],['Digit2','2','Breakout']]},
    snake:{title:'Snake',hint:'Eat the squares and avoid the walls and your tail.',move:'Steer',moveKey:'Arrow keys'},
    breakout:{title:'Breakout',hint:'Move the paddle left or right to bounce the ball into the bricks.',move:'Paddle',moveKey:'← / →'},
  };
  function describe(){
    const zone=zoneManager.activeZone,ride=currentVeh;
    if(zone){
      const kind=zone.zoneClass,instance=zoneManager.loadedModules[zone.id];
      const step=instance?.state;
      const diving=kind==='high-dive'||kind==='diving-contest';
      const pickingHeight=diving&&(step==='select_height'||step==='select');
      const directions=pickingHeight?boards:kind==='arcade'?(arcade[instance?.game]??arcade.menu):activities[kind]??inside;
      if(['done','won','lost','fled'].includes(step))return {id:zone.id,title:zone.label,hint:'Leave to return to the city.',use:'Leave'};
      if(diving&&step==='diving')return {id:zone.id,title:zone.label,hint:'Flip as you fall toward the pool.',action:'Flip',use:'Leave'};
      return {id:zone.id,title:zone.label,use:'Leave',...directions};
    }
    if(zipRiding>=0)return {id:'zipline',title:'Zipline',hint:'Boost to speed up or drop from the cable.',action:'Drop',boost:'Boost'};
    if(ride){
      const type=ride.def.pt,air=type==='air';
      return {id:type,...vehicles[type],move:air?'Steer / tilt':'Steer / throttle',
        action:air?'Rise':'Hop',boost:'Boost',fire:'Shoot',use:'Exit',trick:'Tricks',menus:true};
    }
    if(isFlying)return {id:'flying',...flying};
    if(climbing)return {id:'climb',title:'Climbing',hint:'Use the movement controls along the wall. Jump to push off.',move:'Climb',action:'Jump off'};
    const near=zoneManager.nearestZone;
    return near?{...walk,id:'nearby',hint:'Choose Enter to start '+near.label+'.'}:{id:'walk',...walk};
  }

  const panel=document.getElementById('ow-play-guide'),heading=panel.querySelector('strong');
  const note=panel.querySelector('p'),keyboard=panel.querySelector('ul'),touchChoices=panel.querySelector('.ow-guide-choices');
  const touchLabels={
    action:'btn-jump',boost:'btn-boost',fire:'btn-shoot',use:'btn-enter',trick:'btn-trick',fight:'btn-fight',
  };
  const desktopKeys={move:'WASD / arrows',look:'Mouse',action:'Space',boost:'Shift',fire:'X / click',use:'E',trick:'1–4',fight:'5–8'};
  const quickKeys=[['V','Vehicles'],['B','Weapons'],['C','Style'],['Esc','Pause'],['G','Fullscreen']];
  document.body.classList.add('ow-guided');
  let previous='';
  const showZoneTip=gameAPI.showTip;
  gameAPI.showTip=message=>{
    // Intro and control reminders already have a persistent place in the guide.
    if(zoneManager.transitioning&&zoneManager.interiorGroup)return;
    if(/^(SPACE to flip|Pick height:|Select board height:)/.test(message))return;
    showZoneTip(isMobile?message.replace('Hit SPACE in','Tap Sprint in').replace('Tap SPACE!','Tap Speed up!'):message);
  };
  function keyTag([key,label]){
    const item=document.createElement('li'),tag=document.createElement('kbd'),name=document.createElement('span');
    tag.textContent=key;name.textContent=label;item.append(tag,name);
    return item;
  }
  function tapChoice([code,,label]){
    const action=document.createElement('button');
    action.type='button';action.textContent=label;
    const activate=()=>{
      keys[code]=true;
      setTimeout(()=>{keys[code]=false;},170);
    };
    action.addEventListener('touchstart',event=>{event.preventDefault();activate();},{passive:false});
    action.addEventListener('click',activate);
    return action;
  }
  function update(){
    const menu=menuOpen?'veh-menu':wpnMenuOpen?'wpn-menu':charMenuOpen?'char-menu':'';
    const mobile=isMobile;
    if(menu){
      const subtitle=document.querySelector('#'+menu+' .subtitle');
      const help=mobile?'Tap a choice. Close to resume.'
        :menu==='char-menu'?'Use Tab and Enter to choose. Esc resumes.':'Use the arrows and Enter to choose. Esc resumes play.';
      if(subtitle&&subtitle.textContent!==help)subtitle.textContent=help;
    }
    panel.hidden=!gameStarted||!!menu||gamePaused;
    if(panel.hidden)return;
    const guide=describe(),choices=guide.choices??[];
    const signature=[guide.id,guide.hint,guide.action,guide.use].join('|');
    if(signature===previous)return;
    previous=signature;panel.dataset.situation=guide.id;
    panel.toggleAttribute('data-activity',!!zoneManager.activeZone);
    document.body.toggleAttribute('data-ow-guide-nearby',guide.id==='nearby');
    heading.textContent=guide.title;
    note.textContent=mobile?(guide.touchHint??(guide.look?guide.hint+' Drag to '+guide.look.toLowerCase()+'.':guide.hint)):guide.hint;
    keyboard.replaceChildren(...[
      ...Object.entries(desktopKeys).filter(([id])=>guide[id]).map(([id,key])=>[id==='move'?(guide.moveKey??key):key,guide[id]]),
      ...choices.map(([,key,label])=>[key,label]),...(guide.menus?quickKeys:[['Esc','Pause'],['G','Fullscreen']]),
    ].map(keyTag));
    touchChoices.replaceChildren(...choices.map(tapChoice));
    for(const [role,id] of Object.entries(touchLabels)){
      const target=document.getElementById(id);
      target.hidden=!guide[role];
      if(guide[role])target.textContent=guide[role];
    }
    document.getElementById('mobile-joystick').hidden=!guide.move;
    document.getElementById('mobile-center-btns').hidden=!guide.menus;
    const stick=document.getElementById('ow-guide-stick');
    if(stick&&stick.textContent!==guide.move)stick.textContent=guide.move??'';
  }
  document.getElementById('pause-screen').querySelector('.pause-sub').textContent=isMobile?'Tap to resume':'Esc or click to resume';
  // Read the game state at a low rate to keep DOM work out of the render loop.
  const timer=setInterval(update,120);
  window.addEventListener('pagehide',event=>{if(!event.persisted)clearInterval(timer);});
  return {update};
})();
