import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import Icon from '../../assets/X.svg?react';

export function OceanSimulation() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [showControls, setShowControls] = useState(true);

    useEffect(() => {
        if (!containerRef.current) return;
        const container = containerRef.current;

        // Ensure we don't duplicate renderers on hot reload
        while(container.firstChild) {
            container.removeChild(container.firstChild);
        }

        // --- SCENE SETUP ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xD0EBFF);
        scene.fog = new THREE.FogExp2(0xD0EBFF, 0.015);

        const rect = container.getBoundingClientRect();
        const camera = new THREE.PerspectiveCamera(45, rect.width / rect.height, 0.1, 1000);
        camera.position.set(25, 10, 30);

        const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
        renderer.setSize(rect.width, rect.height);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.target.set(0, -3, 0);
        controls.maxPolarAngle = Math.PI / 2 + 0.1; 
        controls.minDistance = 10;
        controls.maxDistance = 100;

        // --- LIGHTING ---
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);

        const sunLight = new THREE.DirectionalLight(0xfff5e6, 1.2);
        sunLight.position.set(50, 40, -20);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 150;
        sunLight.shadow.camera.left = -40;
        sunLight.shadow.camera.right = 40;
        sunLight.shadow.camera.top = 40;
        sunLight.shadow.camera.bottom = -40;
        sunLight.shadow.bias = -0.0005;
        scene.add(sunLight);

        const waterLight = new THREE.DirectionalLight(0x0077ff, 0.6);
        waterLight.position.set(0, -50, 0);
        scene.add(waterLight);

        // --- MATERIALS ---
        const colors = {
            foundation: 0x8b7355,   
            outerFrame: 0x1a1a1a,   
            innerFrame: 0x808080,   // Updated to #808080
            cylinders: 0xa5b51c,    // Updated to #a5b51c
            generator: 0x90959e,    
            belt: 0x333333,         
            seabed: 0x9c8b74,
            water: 0x0055a4
        };

        const matFoundation = new THREE.MeshStandardMaterial({ color: colors.foundation, roughness: 0.9, metalness: 0.1 });
        const matOuterFrame = new THREE.MeshStandardMaterial({ color: colors.outerFrame, roughness: 0.7, metalness: 0.6 });
        const matInnerFrame = new THREE.MeshStandardMaterial({ color: colors.innerFrame, roughness: 0.5, metalness: 0.8 });
        const matCylinder = new THREE.MeshStandardMaterial({ color: colors.cylinders, roughness: 0.4, metalness: 0.3 });
        const matGenerator = new THREE.MeshStandardMaterial({ color: colors.generator, roughness: 0.6, metalness: 0.5 });
        const matBelt = new THREE.MeshStandardMaterial({ color: colors.belt, roughness: 0.8, metalness: 0.1 });

        // --- ENVIRONMENT (Seabed) ---
        const seabedGeo = new THREE.PlaneGeometry(200, 200, 32, 32);
        const seabedPos = seabedGeo.attributes.position;
        for(let i=0; i<seabedPos.count; i++) {
            const z = seabedPos.getZ(i);
            seabedPos.setZ(i, z + (Math.random() * 0.5 - 0.25));
        }
        seabedGeo.computeVertexNormals();

        const matSeabed = new THREE.MeshStandardMaterial({ color: colors.seabed, roughness: 0.9, metalness: 0.0 });
        const seabed = new THREE.Mesh(seabedGeo, matSeabed);
        seabed.rotation.x = -Math.PI / 2;
        seabed.position.y = -15; 
        seabed.receiveShadow = true;
        scene.add(seabed);

        // --- DEVICE CONSTRUCTION (OSWEC) ---
        const deviceGroup = new THREE.Group();
        // Rotate the entire device by 90 degrees so it faces the waves (which travel along the X axis)
        deviceGroup.rotation.y = -Math.PI / 2;
        scene.add(deviceGroup);

        const baseWidth = 18;
        const baseDepth = 14;
        const topWidth = 18;
        const topDepth = 6;
        const height = 18;

        // 1. Foundation (4 blocks)
        const foundGeo = new THREE.CylinderGeometry(1.5, 2.5, 2, 4);
        foundGeo.rotateY(Math.PI / 4); 
        const foundationPositions = [
            [-baseWidth/2, baseDepth/2],
            [baseWidth/2, baseDepth/2],
            [-baseWidth/2, -baseDepth/2],
            [baseWidth/2, -baseDepth/2]
        ];
        foundationPositions.forEach(pos => {
            const block = new THREE.Mesh(foundGeo, matFoundation);
            block.position.set(pos[0], -14, pos[1]);
            block.castShadow = true;
            block.receiveShadow = true;
            deviceGroup.add(block);
        });

        // 2. Outer Frame
        const beamSize = 0.6;
        const frameGeo = new THREE.BoxGeometry(beamSize, beamSize, beamSize);

        const createBeam = (l: number, x: number, y: number, z: number, axis: 'x'|'y'|'z') => {
            const mesh = new THREE.Mesh(frameGeo, matOuterFrame);
            if (axis === 'x') mesh.scale.set(l / beamSize, 1, 1);
            else if (axis === 'y') mesh.scale.set(1, l / beamSize, 1);
            else if (axis === 'z') mesh.scale.set(1, 1, l / beamSize);
            mesh.position.set(x, y, z);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            deviceGroup.add(mesh);
            return mesh;
        };

        createBeam(baseWidth + beamSize, 0, -12.7, baseDepth/2, 'x'); 
        createBeam(baseWidth + beamSize, 0, -12.7, -baseDepth/2, 'x'); 
        createBeam(baseDepth - beamSize, -baseWidth/2, -12.7, 0, 'z'); 
        createBeam(baseDepth - beamSize, baseWidth/2, -12.7, 0, 'z'); 

        createBeam(topWidth + beamSize, 0, -12.7 + height, topDepth/2, 'x'); 
        createBeam(topWidth + beamSize, 0, -12.7 + height, -topDepth/2, 'x'); 
        createBeam(topDepth - beamSize, -topWidth/2, -12.7 + height, 0, 'z'); 
        createBeam(topDepth - beamSize, topWidth/2, -12.7 + height, 0, 'z'); 

        const createPillar = (x: number, z1: number, z2: number) => {
            const pt1 = new THREE.Vector3(x, -12.7, z1);
            const pt2 = new THREE.Vector3(x, -12.7 + height, z2);
            const dist = pt1.distanceTo(pt2);
            
            const geom = new THREE.BoxGeometry(beamSize, dist, beamSize);
            geom.translate(0, dist / 2, 0); 
            
            const mesh = new THREE.Mesh(geom, matOuterFrame);
            mesh.position.copy(pt1);
            mesh.lookAt(pt2);
            mesh.rotateX(Math.PI / 2); 

            mesh.castShadow = true;
            mesh.receiveShadow = true;
            deviceGroup.add(mesh);
        };

        createPillar(-baseWidth/2, baseDepth/2, topDepth/2); 
        createPillar(baseWidth/2, baseDepth/2, topDepth/2);  
        createPillar(-baseWidth/2, -baseDepth/2, -topDepth/2); 
        createPillar(baseWidth/2, -baseDepth/2, -topDepth/2);  

        const midDepth = (baseDepth + topDepth) / 2;
        createBeam(midDepth, -baseWidth/2, -12.7 + height/2, 0, 'z');
        createBeam(midDepth, baseWidth/2, -12.7 + height/2, 0, 'z');

        // 3. Main Shaft and Bearings
        const pivotZ = 0; 
        const pivotY = -12;
        
        createBeam(baseWidth, 0, -12.7, pivotZ, 'x');

        const shaftLen = baseWidth + 5;
        const shaftGeo = new THREE.CylinderGeometry(0.35, 0.35, shaftLen, 16);
        const shaft = new THREE.Mesh(shaftGeo, matInnerFrame);
        shaft.rotation.z = Math.PI / 2;
        shaft.position.set(1.5, pivotY, pivotZ); 
        shaft.castShadow = true;
        deviceGroup.add(shaft);

        for (let i = 0; i < 4; i++) {
            const bx = -baseWidth/2 + 2 + i * ((baseWidth - 4) / 3);
            const bearing = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 1.2), matInnerFrame);
            bearing.position.set(bx, -12.7 + 0.6, pivotZ);
            bearing.castShadow = true;
            deviceGroup.add(bearing);
        }

        // 4. Inner Flap (Pendulum) Group
        const flapPivot = new THREE.Group();
        flapPivot.position.set(0, pivotY, pivotZ);
        deviceGroup.add(flapPivot);

        const innerFrameWidth = baseWidth - 4; 
        const innerFrameHeight = 15.5;
        const frameThick = 0.5;
        const frameDepth = 0.8;
        
        const createInnerBeam = (w: number, h: number, d: number, x: number, y: number, z: number) => {
            const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), matInnerFrame);
            mesh.position.set(x, y, z);
            mesh.castShadow = true;
            flapPivot.add(mesh);
        };

        createInnerBeam(frameThick, innerFrameHeight + frameThick*2, frameDepth, -innerFrameWidth/2, innerFrameHeight/2, 0);
        createInnerBeam(frameThick, innerFrameHeight + frameThick*2, frameDepth, innerFrameWidth/2, innerFrameHeight/2, 0);
        createInnerBeam(innerFrameWidth, frameThick, frameDepth, 0, innerFrameHeight + frameThick, 0);
        createInnerBeam(innerFrameWidth, frameThick, frameDepth, 0, -frameThick, 0);
        createInnerBeam(innerFrameWidth, frameThick, frameDepth, 0, innerFrameHeight * 0.33, 0);
        createInnerBeam(innerFrameWidth, frameThick, frameDepth, 0, innerFrameHeight * 0.66, 0);

        const cylRadius = 0.6;
        const cylSpacing = 1.23; 
        for (let i = 0; i < 12; i++) {
            const cylGeo = new THREE.CylinderGeometry(cylRadius, cylRadius, innerFrameWidth - frameThick, 32);
            const cyl = new THREE.Mesh(cylGeo, matCylinder);
            cyl.rotation.z = Math.PI / 2;
            cyl.position.set(0, (i * cylSpacing) + cylRadius + 0.25, 0);
            cyl.castShadow = true;
            flapPivot.add(cyl);
        }

        // 5. PTO (Generator, Pulleys, Belt)
        const ptoGroup = new THREE.Group();
        deviceGroup.add(ptoGroup);

        const genW = 5, genH = 2.5, genD = 3.5;
        const genBox = new THREE.Mesh(new THREE.BoxGeometry(genW, genH, genD), matGenerator);
        genBox.position.set(baseWidth/2 - genW/2, -12.7 + height + genH/2, pivotZ);
        genBox.castShadow = true;
        ptoGroup.add(genBox);

        const pulleyThick = 0.6;
        const topPulleyRadius = 0.6;
        const topPulleyY = -12.7 + height + genH/2;
        const topPulleyX = baseWidth/2 + 2.5; 
        
        const topPulleyGeo = new THREE.CylinderGeometry(topPulleyRadius, topPulleyRadius, pulleyThick, 32);
        const topPulley = new THREE.Mesh(topPulleyGeo, matInnerFrame);
        topPulley.rotation.set(0, 0, Math.PI / 2);
        topPulley.position.set(topPulleyX, topPulleyY, pivotZ);
        topPulley.castShadow = true;
        ptoGroup.add(topPulley);

        const genShaftGeo = new THREE.CylinderGeometry(0.2, 0.2, 2.5, 16);
        const genShaft = new THREE.Mesh(genShaftGeo, matInnerFrame);
        genShaft.rotation.set(0, 0, Math.PI / 2);
        genShaft.position.set(topPulleyX - 1.25, topPulleyY, pivotZ);
        genShaft.castShadow = true;
        ptoGroup.add(genShaft);

        const largePulleyRadius = 2.8;
        
        const pulleyShape = new THREE.Shape();
        pulleyShape.absarc(0, 0, largePulleyRadius, 0, Math.PI * 2, false);
        
        for(let i=0; i<6; i++) {
            const angle = (Math.PI * 2 / 6) * i;
            const r = largePulleyRadius * 0.65;
            const holePath = new THREE.Path();
            holePath.absarc(Math.cos(angle)*r, Math.sin(angle)*r, 0.7, 0, Math.PI * 2, true);
            pulleyShape.holes.push(holePath);
        }
        
        const extrudeSettings = {
            depth: pulleyThick,
            bevelEnabled: false,
            curveSegments: 32
        };
        const largePulleyGeo = new THREE.ExtrudeGeometry(pulleyShape, extrudeSettings);
        largePulleyGeo.translate(0, 0, -pulleyThick / 2); // Center along extrusion axis

        const largePulley = new THREE.Mesh(largePulleyGeo, matInnerFrame);
        // ExtrudeGeometry extrudes along Z. Rotate Y by 90 to align main axis with X.
        largePulley.rotation.set(0, Math.PI / 2, 0);
        largePulley.position.set(topPulleyX, pivotY, pivotZ); 
        largePulley.castShadow = true;
        
        deviceGroup.add(largePulley);

        const beltThickness = 0.15;
        const beltWidth = 0.45;
        const distY = topPulleyY - pivotY; 
        const radiusDiff = largePulleyRadius - topPulleyRadius;
        const beltLength = Math.hypot(distY, radiusDiff);
        const beltAngle = Math.asin(radiusDiff / beltLength);
        
        const createBeltSegment = (side: 1 | -1) => {
            const geo = new THREE.BoxGeometry(beltWidth, beltLength, beltThickness);
            const mesh = new THREE.Mesh(geo, matBelt);
            
            const cx = topPulleyX;
            const cy = pivotY + distY / 2;
            const cz = pivotZ;
            
            const avgRadius = (largePulleyRadius + topPulleyRadius) / 2;
            mesh.position.set(cx, cy, cz + side * avgRadius);
            
            // Invert the rotation so the belt leans inwards at the top (A-shape) instead of outwards
            mesh.rotation.x = -side * beltAngle;
            mesh.castShadow = true;
            return mesh;
        };
        
        deviceGroup.add(createBeltSegment(1));
        deviceGroup.add(createBeltSegment(-1));

        // --- WATER SIMULATION ---
        const waterSize = 150;
        const waterSegments = 120;
        const waterGeo = new THREE.PlaneGeometry(waterSize, waterSize, waterSegments, waterSegments);
        waterGeo.rotateX(-Math.PI / 2);

        const originalPositions = new Float32Array(waterGeo.attributes.position.array);
        waterGeo.userData = { originalPositions };

        const waterMat = new THREE.MeshPhysicalMaterial({
            color: colors.water,
            transparent: true,
            opacity: 0.75,
            roughness: 0.1,
            metalness: 0.1,
            transmission: 0.6,
            ior: 1.33,
            side: THREE.DoubleSide,
            flatShading: true
        });

        const water = new THREE.Mesh(waterGeo, waterMat);
        water.position.y = 0; 
        water.receiveShadow = true;
        scene.add(water);

        // --- WAVE & PHYSICS LOGIC ---
        let time = 0;
        const clock = new THREE.Clock();

        const waveAmplitude = 1.5;
        const waveFrequency = 1.2;
        const waveLength = 0.15; 

        function getWaveHeight(x: number, z: number, t: number) {
            let y = 0;
            y += Math.sin(x * waveLength - t * waveFrequency) * waveAmplitude;
            y += Math.sin(x * (waveLength * 2.1) + z * 0.1 - t * (waveFrequency * 1.5)) * (waveAmplitude * 0.2);
            y += Math.sin(x * (waveLength * 0.5) - z * 0.2 - t * (waveFrequency * 0.8)) * (waveAmplitude * 0.1);
            return y;
        }

        let animationId: number;

        // --- ANIMATION LOOP ---
        function animate() {
            animationId = requestAnimationFrame(animate);

            const delta = clock.getDelta();
            time += delta;

            const positions = water.geometry.attributes.position;
            const orig = water.geometry.userData.originalPositions;

            for (let i = 0; i < positions.count; i++) {
                const x = orig[i * 3];     
                const z = orig[i * 3 + 2]; 
                
                const newY = getWaveHeight(x, z, time);
                
                positions.setY(i, newY);
            }
            
            positions.needsUpdate = true;
            water.geometry.computeVertexNormals();
            
            // Calculate a target angle based on wave elevation/amplitude ratio
            const phaseDelay = -0.4; 
            const surgeForce = Math.sin(-time * waveFrequency + phaseDelay) * waveAmplitude;
            const maxAngle = 0.6; 
            const targetRotationX = (surgeForce / 3.5) * maxAngle; 

            flapPivot.rotation.x += (targetRotationX - flapPivot.rotation.x) * 0.08;

            // Optional: Also gently rotate the large pulley visually!
            largePulley.rotation.x = flapPivot.rotation.x;
            
            controls.update();
            renderer.render(scene, camera);
        }

        animate();

        // Handle Window Resize via ResizeObserver to track the container div properly
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                camera.aspect = width / height;
                camera.updateProjectionMatrix();
                renderer.setSize(width, height);
            }
        });
        resizeObserver.observe(container);

        // Cleanup
        return () => {
            resizeObserver.disconnect();
            cancelAnimationFrame(animationId);
            renderer.dispose();
            if (container.contains(renderer.domElement)) {
                container.removeChild(renderer.domElement);
            }
        };
    }, []);

    return (
        <div className="relative w-full h-full rounded-lg overflow-hidden isolate outline outline-1 outline-sky-500/20">
            <div ref={containerRef} className="w-full h-full bg-sky-200/50" />
            {showControls && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/60 text-white pl-4 pr-2 py-2 rounded-full text-xs font-medium font-['Inter'] flex items-center gap-0.5 backdrop-blur-sm whitespace-nowrap shadow-lg transition-all">
                    <span>Left Click: Rotate | Right Click: Pan | Scroll: Zoom</span>
                    <button 
                        onClick={() => setShowControls(false)}
                        className="w-5 h-5 rounded-full hover:bg-white/20 flex items-center justify-center transition-colors shrink-0"
                        title="Dismiss"
                    >
                        <Icon className="size-3 text-white stroke-white stroke-[0.8px]"/>
                    </button>
                </div>
            )}
        </div>
    );
}
