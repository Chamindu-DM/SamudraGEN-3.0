import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export function OceanSimulation() {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current) return;
        const container = containerRef.current;

        // Ensure we don't duplicate renderers on hot reload
        while(container.firstChild) {
            container.removeChild(container.firstChild);
        }

        // --- SCENE SETUP ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xb0d5ce);
        scene.fog = new THREE.FogExp2(0xb0d5ce, 0.015);

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
            yellowFlap: 0xffcc00,
            darkMetal: 0x2a2e35,
            lightMetal: 0x5a606b,
            seabed: 0x9c8b74,
            water: 0x0055a4
        };

        const matFlap = new THREE.MeshStandardMaterial({ color: colors.yellowFlap, roughness: 0.3, metalness: 0.2 });
        const matBase = new THREE.MeshStandardMaterial({ color: colors.darkMetal, roughness: 0.7, metalness: 0.5 });
        const matPin = new THREE.MeshStandardMaterial({ color: colors.lightMetal, roughness: 0.4, metalness: 0.8 });

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
        scene.add(deviceGroup);

        const baseWidth = 10;
        const baseLength = 16;
        const baseHeight = 2;
        
        const baseMesh = new THREE.Mesh(new THREE.BoxGeometry(baseLength, baseHeight, baseWidth), matBase);
        baseMesh.position.y = -15 + baseHeight/2;
        baseMesh.receiveShadow = true;
        baseMesh.castShadow = true;
        deviceGroup.add(baseMesh);

        const supportGeo = new THREE.BoxGeometry(4, 3, 2);
        const supportLeft = new THREE.Mesh(supportGeo, matBase);
        supportLeft.position.set(0, -15 + baseHeight + 1.5, baseWidth/2 - 1);
        supportLeft.castShadow = true;
        deviceGroup.add(supportLeft);

        const supportRight = new THREE.Mesh(supportGeo, matBase);
        supportRight.position.set(0, -15 + baseHeight + 1.5, -baseWidth/2 + 1);
        supportRight.castShadow = true;
        deviceGroup.add(supportRight);

        const flapPivot = new THREE.Group();
        const pivotY = -15 + baseHeight + 1.5; 
        flapPivot.position.set(0, pivotY, 0);
        deviceGroup.add(flapPivot);

        const pinGeo = new THREE.CylinderGeometry(0.6, 0.6, baseWidth + 1, 16);
        const pin = new THREE.Mesh(pinGeo, matPin);
        pin.rotation.x = Math.PI / 2;
        pin.castShadow = true;
        flapPivot.add(pin);

        const flapAssembly = new THREE.Group();
        flapPivot.add(flapAssembly);

        const plateGeo = new THREE.BoxGeometry(2, 12, 0.5);
        const plateLeft = new THREE.Mesh(plateGeo, matFlap);
        plateLeft.position.set(0, 6, baseWidth/2 - 1.5);
        plateLeft.castShadow = true;
        flapAssembly.add(plateLeft);

        const plateRight = new THREE.Mesh(plateGeo, matFlap);
        plateRight.position.set(0, 6, -baseWidth/2 + 1.5);
        plateRight.castShadow = true;
        flapAssembly.add(plateRight);

        const chamberRadius = 1.2;
        const chamberLength = baseWidth - 3;
        const chamberGeo = new THREE.CylinderGeometry(chamberRadius, chamberRadius, chamberLength, 32);
        
        for(let i=0; i<3; i++) {
            const chamber = new THREE.Mesh(chamberGeo, matFlap);
            chamber.rotation.x = Math.PI / 2;
            chamber.position.set(0, 3 + (i * 3.5), 0);
            chamber.castShadow = true;
            chamber.receiveShadow = true;
            flapAssembly.add(chamber);
        }

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
            const targetRotationZ = (surgeForce / 3.5) * maxAngle; 

            flapPivot.rotation.z += (targetRotationZ - flapPivot.rotation.z) * 0.08;

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
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/60 text-white px-4 py-2 rounded-full text-xs font-medium font-['Inter'] pointer-events-none flex items-center gap-2 backdrop-blur-sm whitespace-nowrap">
                Left Click: Rotate | Right Click: Pan | Scroll: Zoom
            </div>
        </div>
    );
}
