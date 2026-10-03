import * as THREE from "three";
export function createScene(container: HTMLElement): () => void {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "low-power",
    });
  } catch {
    return () => {};
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.z = 7;
  const group = new THREE.Group();
  scene.add(group);
  const positions: number[] = [];
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < 34; i++) {
    const angle = i * 2.39996;
    const y = 1 - (i / 33) * 2;
    const radius = Math.sqrt(1 - y * y);
    const p = new THREE.Vector3(
      Math.cos(angle) * radius * 2.5,
      y * 1.8,
      Math.sin(angle) * radius * 1.2,
    );
    points.push(p);
    positions.push(p.x, p.y, p.z);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  const material = new THREE.PointsMaterial({
    color: 0xc9a4ff,
    size: 0.045,
    transparent: true,
    opacity: 0.75,
  });
  group.add(new THREE.Points(geometry, material));
  const linePositions: number[] = [];
  points.forEach((p, i) =>
    points.slice(i + 1).forEach((q) => {
      if (p.distanceTo(q) < 1.45)
        linePositions.push(p.x, p.y, p.z, q.x, q.y, q.z);
    }),
  );
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(linePositions, 3),
  );
  const lineMaterial = new THREE.LineBasicMaterial({
    color: 0x9871c4,
    transparent: true,
    opacity: 0.2,
  });
  group.add(new THREE.LineSegments(lineGeometry, lineMaterial));
  const resize = () => {
    const w = container.clientWidth,
      h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  resize();
  const pointer = { x: 0, y: 0 };
  const parent = container.parentElement!;
  const move = (ev: PointerEvent) => {
    const rect = parent.getBoundingClientRect();
    pointer.x = (ev.clientX - rect.left) / rect.width - 0.5;
    pointer.y = (ev.clientY - rect.top) / rect.height - 0.5;
  };
  parent.addEventListener("pointermove", move);
  let frame = 0;
  let visible = true;
  let previous = 0;
  const visibility = new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
  });
  visibility.observe(container);
  const tick = (time: number) => {
    frame = requestAnimationFrame(tick);
    if (!visible || document.hidden || time - previous < 32) return;
    previous = time;
    group.rotation.y +=
      (pointer.x * 0.25 + Math.sin(time * 0.00007) * 0.15 - group.rotation.y) *
      0.03;
    group.rotation.x += (pointer.y * 0.15 - group.rotation.x) * 0.03;
    group.rotation.z = time * 0.000015;
    renderer.render(scene, camera);
  };
  frame = requestAnimationFrame(tick);
  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    visibility.disconnect();
    parent.removeEventListener("pointermove", move);
    geometry.dispose();
    material.dispose();
    lineGeometry.dispose();
    lineMaterial.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
}
