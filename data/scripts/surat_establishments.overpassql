[out:json][timeout:120];
(
  node["amenity"~"pharmacy|cafe|fuel|police|hospital|restaurant"](21.10,72.75,21.25,72.90);
  node["shop"~"convenience|supermarket"](21.10,72.75,21.25,72.90);
);
out body;
