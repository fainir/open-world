// Zone Registry — builds zone definitions from captured building positions + fixed locations
// `enterableSpots` is passed in from index.html (captured during building generation)

export function buildZones(spots){
  const zones=[];
  // Pick first few of each building type as enterable
  const restaurants=spots.filter(s=>s.type==='restaurant');
  const shops=spots.filter(s=>s.type==='shop');
  const raves=spots.filter(s=>s.type==='rave');

  // ─── INTERIORS (from city buildings) ───
  // Coffee shops (first 3 restaurants)
  for(let i=0;i<Math.min(3,restaurants.length);i++){
    const s=restaurants[i];
    zones.push({id:'coffee-'+i,type:'interior',module:'./zones/coffee-shop.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Coffee Shop',icon:'\u2615'});
  }
  // Bars (next 3 restaurants)
  for(let i=3;i<Math.min(6,restaurants.length);i++){
    const s=restaurants[i];
    zones.push({id:'bar-'+(i-3),type:'interior',module:'./zones/bar.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Bar',icon:'\u{1F37A}'});
  }
  // Clothing stores (first 3 shops)
  for(let i=0;i<Math.min(3,shops.length);i++){
    const s=shops[i];
    zones.push({id:'clothing-'+i,type:'interior',module:'./zones/clothing-store.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Clothing Store',icon:'\u{1F45A}'});
  }
  // Convenience stores (next 3 shops)
  for(let i=3;i<Math.min(6,shops.length);i++){
    const s=shops[i];
    zones.push({id:'convenience-'+(i-3),type:'interior',module:'./zones/convenience-store.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Convenience Store',icon:'\u{1F3EA}'});
  }
  // Rave interiors (first 3 raves)
  for(let i=0;i<Math.min(3,raves.length);i++){
    const s=raves[i];
    zones.push({id:'rave-'+i,type:'interior',module:'./zones/rave-interior.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Nightclub',icon:'\u{1F3B6}'});
  }
  // Restaurant interiors (next batch)
  for(let i=6;i<Math.min(9,restaurants.length);i++){
    const s=restaurants[i];
    zones.push({id:'restaurant-'+(i-6),type:'interior',module:'./zones/restaurant-interior.js',
      position:[s.cx,0,s.cz+2],radius:5,label:'Restaurant',icon:'\u{1F37D}'});
  }

  // ─── MISSIONS (at sports complex, SX=380 SZ=850) ───
  zones.push({id:'tennis-match',type:'mission',module:'./zones/tennis-match.js',
    position:[440,0,750],radius:8,label:'Tennis Match',icon:'\u{1F3BE}'});
  zones.push({id:'basketball-game',type:'mission',module:'./zones/basketball-game.js',
    position:[360,0,750],radius:8,label:'Basketball Game',icon:'\u{1F3C0}'});
  zones.push({id:'boxing-match',type:'mission',module:'./zones/boxing-match.js',
    position:[455,0,915],radius:8,label:'Boxing Match',icon:'\u{1F94A}'});
  zones.push({id:'swimming-race',type:'mission',module:'./zones/swimming-race.js',
    position:[500,0,770],radius:8,label:'Swimming Race',icon:'\u{1F3CA}'});
  zones.push({id:'archery-challenge',type:'mission',module:'./zones/archery-challenge.js',
    position:[310,0,980],radius:8,label:'Archery Challenge',icon:'\u{1F3AF}'});

  return zones;
}
