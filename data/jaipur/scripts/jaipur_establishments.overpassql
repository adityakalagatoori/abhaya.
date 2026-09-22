[out:json][timeout:120];
(
  node["amenity"~"^(pharmacy|cafe|fuel|police|hospital|restaurant)$"](26.80,75.70,27.00,75.95);
  node["shop"~"^(convenience|supermarket)$"](26.80,75.70,27.00,75.95);
);
out body;
