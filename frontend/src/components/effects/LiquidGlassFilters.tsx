"use client";

import { useEffect } from "react";

export default function LiquidGlassFilters() {
  useEffect(() => {
    generateLiquidMaps();
  }, []);

  return (
    <svg 
      id="liquid-glass-svg" 
      style={{ 
        position: "absolute", 
        width: 0, 
        height: 0, 
        pointerEvents: "none" 
      }}
    >
      <defs>
        <filter 
          id="liquidFilter" 
          x="-50%" 
          y="-50%" 
          width="200%" 
          height="200%"
        >
          <feImage 
            id="circle-map" 
            href="" 
            result="map" 
          />
          <feDisplacementMap 
            in="SourceGraphic" 
            in2="map" 
            scale="40" 
            xChannelSelector="R" 
            yChannelSelector="G" 
            result="refracted"
          />
          <feSpecularLighting 
            in="SourceAlpha" 
            surfaceScale="1.5" 
            specularConstant="0.8" 
            specularExponent="30" 
            lightingColor="#ffffff" 
            result="rim"
          >
            <fePointLight x="-3000" y="-6000" z="400"/>
          </feSpecularLighting>
          <feComposite 
            in="rim" 
            in2="SourceAlpha" 
            operator="in" 
            result="rim_clipped"
          />
          <feBlend 
            in="rim_clipped" 
            in2="refracted" 
            mode="screen"
          />
        </filter>

        <filter 
          id="squircleFilter" 
          x="-50%" 
          y="-50%" 
          width="200%" 
          height="200%"
        >
          <feImage 
            id="squircle-map" 
            href="" 
            result="map" 
          />
          <feDisplacementMap 
            in="SourceGraphic" 
            in2="map" 
            scale="40" 
            xChannelSelector="R" 
            yChannelSelector="G" 
            result="refracted"
          />
          <feSpecularLighting 
            in="SourceAlpha" 
            surfaceScale="1.5" 
            specularConstant="0.8" 
            specularExponent="30" 
            lightingColor="#ffffff" 
            result="rim"
          >
            <fePointLight x="-3000" y="-6000" z="400"/>
          </feSpecularLighting>
          <feComposite 
            in="rim" 
            in2="SourceAlpha" 
            operator="in" 
            result="rim_clipped"
          />
          <feBlend 
            in="rim_clipped" 
            in2="refracted" 
            mode="screen"
          />
        </filter>
      </defs>
    </svg>
  );
}

function generateLiquidMaps() {
  const size = 512;
  const center = size / 2;
  const radius = size / 2;
  
  // Create canvases
  const cCanvas = document.createElement('canvas');
  const sCanvas = document.createElement('canvas');
  cCanvas.width = sCanvas.width = size;
  cCanvas.height = sCanvas.height = size;
  
  const cCtx = cCanvas.getContext('2d');
  const sCtx = sCanvas.getContext('2d');
  
  if (!cCtx || !sCtx) return;
  
  const cData = cCtx.createImageData(size, size);
  const sData = sCtx.createImageData(size, size);

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      const nx = (x - center) / radius;
      const ny = (y - center) / radius;

      // CIRCLE PHYSICS
      const cDist = Math.sqrt(nx * nx + ny * ny);
      if (cDist < 1.0) {
        const height = Math.sqrt(1 - Math.pow(cDist, 2));
        const normalX = nx / Math.max(0.01, height);
        const normalY = ny / Math.max(0.01, height);
        cData.data[idx] = 128 + normalX * 127;
        cData.data[idx + 1] = 128 + normalY * 127;
        cData.data[idx + 2] = 128;
        cData.data[idx + 3] = 255;
      } else {
        cData.data[idx] = cData.data[idx + 1] = 128;
        cData.data[idx + 3] = 255;
      }

      // SQUIRCLE PHYSICS
      const distS = Math.pow(Math.pow(nx, 4) + Math.pow(ny, 4), 1/4);
      if (distS < 1.0) {
        const sHeight = Math.sqrt(1 - Math.pow(distS, 2.5));
        const sSlope = (2.5 * Math.pow(distS, 1.5)) / (2 * Math.max(0.01, sHeight));
        sData.data[idx] = 128 + nx * sSlope * 127;
        sData.data[idx + 1] = ny * sSlope * 127 + 128;
        sData.data[idx + 2] = 128;
        sData.data[idx + 3] = 255;
      } else {
        sData.data[idx] = sData.data[idx + 1] = 128;
        sData.data[idx + 3] = 255;
      }
    }
  }
  
  cCtx.putImageData(cData, 0, 0);
  sCtx.putImageData(sData, 0, 0);
  
  const circleMap = document.getElementById('circle-map') as any;
  const squircleMap = document.getElementById('squircle-map') as any;
  
  if (circleMap) circleMap.setAttribute('href', cCanvas.toDataURL());
  if (squircleMap) squircleMap.setAttribute('href', sCanvas.toDataURL());
}