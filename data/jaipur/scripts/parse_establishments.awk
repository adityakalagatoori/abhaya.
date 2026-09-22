BEGIN {
  print "osm_id,lat,lon,name,amenity,shop,opening_hours,phone"
}
/"type": "node"/ { id=""; lat=""; lon=""; name=""; amenity=""; shop=""; hours=""; phone=""; intags=0; next }
id=="" && /"id":/ { match($0, /[0-9]+/); id = substr($0, RSTART, RLENGTH); next }
lat=="" && /"lat":/ { match($0, /-?[0-9.]+/); lat = substr($0, RSTART, RLENGTH); next }
lon=="" && /"lon":/ { match($0, /-?[0-9.]+/); lon = substr($0, RSTART, RLENGTH); next }
/"tags": \{/ { intags=1; next }
intags && /"name":/ { match($0, /"name": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"name": "/,"",s); sub(/"$/,"",s); gsub(/,/,";",s); name=s; next }
intags && /"amenity":/ { match($0, /"amenity": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"amenity": "/,"",s); sub(/"$/,"",s); amenity=s; next }
intags && /"shop":/ { match($0, /"shop": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"shop": "/,"",s); sub(/"$/,"",s); shop=s; next }
intags && /"opening_hours":/ { match($0, /"opening_hours": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"opening_hours": "/,"",s); sub(/"$/,"",s); gsub(/,/,";",s); hours=s; next }
intags && /"phone":/ { match($0, /"phone": "[^"]*"/); s=substr($0,RSTART,RLENGTH); sub(/"phone": "/,"",s); sub(/"$/,"",s); phone=s; next }
intags && /^\s*\},?\s*$/ { intags=0; next }
!intags && /^\},?\s*$/ { if (id != "" && lat != "") { print id "," lat "," lon "," name "," amenity "," shop "," hours "," phone }; id="" }
