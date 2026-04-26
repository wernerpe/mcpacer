<script lang="ts">
	type View = 'front' | 'back';
	type PaintMode = 'add' | 'remove';

	type RectRegion = {
		id: string;
		label: string;
		view: View;
		shape: 'rect';
		x: number;
		y: number;
		w: number;
		h: number;
		rx?: number;
	};
	type EllipseRegion = {
		id: string;
		label: string;
		view: View;
		shape: 'ellipse';
		cx: number;
		cy: number;
		rx: number;
		ry: number;
	};
	type CircleRegion = {
		id: string;
		label: string;
		view: View;
		shape: 'circle';
		cx: number;
		cy: number;
		r: number;
	};
	type Region = RectRegion | EllipseRegion | CircleRegion;

	let {
		view,
		selectedRegions = [],
		highlightedRegions = [],
		onRegionsChange
	}: {
		view: View;
		selectedRegions?: string[];
		highlightedRegions?: string[];
		onRegionsChange?: (regions: string[]) => void;
	} = $props();

	let hoveredRegion: string | null = $state(null);
	let painting: boolean = $state(false);
	let paintMode: PaintMode = $state('add');

	let working: Set<string> = $state(new Set(selectedRegions));

	$effect(() => {
		if (!painting) {
			working = new Set(selectedRegions);
		}
	});

	const FRONT_REGIONS: Region[] = [
		// Core
		{ id: 'core', label: 'Core / abdominals', view: 'front', shape: 'rect', x: 80, y: 110, w: 40, h: 50, rx: 8 },

		// Hip area
		{ id: 'left_tfl', label: 'TFL / hip outer (L)', view: 'front', shape: 'ellipse', cx: 70, cy: 178, rx: 6, ry: 10 },
		{ id: 'right_tfl', label: 'TFL / hip outer (R)', view: 'front', shape: 'ellipse', cx: 130, cy: 178, rx: 6, ry: 10 },
		{ id: 'left_hip_flexor', label: 'Hip flexor (L)', view: 'front', shape: 'ellipse', cx: 84, cy: 184, rx: 9, ry: 9 },
		{ id: 'right_hip_flexor', label: 'Hip flexor (R)', view: 'front', shape: 'ellipse', cx: 116, cy: 184, rx: 9, ry: 9 },
		{ id: 'left_adductor', label: 'Adductor / inner thigh (L)', view: 'front', shape: 'rect', x: 94, y: 195, w: 6, h: 70, rx: 3 },
		{ id: 'right_adductor', label: 'Adductor / inner thigh (R)', view: 'front', shape: 'rect', x: 100, y: 195, w: 6, h: 70, rx: 3 },

		// Quads
		{ id: 'left_quad_upper', label: 'Upper quad (L)', view: 'front', shape: 'rect', x: 70, y: 198, w: 24, h: 25, rx: 6 },
		{ id: 'left_quad_mid', label: 'Mid quad (L)', view: 'front', shape: 'rect', x: 70, y: 223, w: 24, h: 25, rx: 6 },
		{ id: 'left_quad_lower', label: 'Lower quad (L)', view: 'front', shape: 'rect', x: 70, y: 248, w: 24, h: 25, rx: 6 },
		{ id: 'right_quad_upper', label: 'Upper quad (R)', view: 'front', shape: 'rect', x: 106, y: 198, w: 24, h: 25, rx: 6 },
		{ id: 'right_quad_mid', label: 'Mid quad (R)', view: 'front', shape: 'rect', x: 106, y: 223, w: 24, h: 25, rx: 6 },
		{ id: 'right_quad_lower', label: 'Lower quad (R)', view: 'front', shape: 'rect', x: 106, y: 248, w: 24, h: 25, rx: 6 },

		// Knee
		{ id: 'left_knee_outer', label: 'Knee — outer (L)', view: 'front', shape: 'ellipse', cx: 72, cy: 287, rx: 6, ry: 9 },
		{ id: 'left_knee_front', label: 'Knee — front (L)', view: 'front', shape: 'circle', cx: 84, cy: 287, r: 7 },
		{ id: 'left_knee_inner', label: 'Knee — inner (L)', view: 'front', shape: 'ellipse', cx: 95, cy: 287, rx: 6, ry: 9 },
		{ id: 'right_knee_inner', label: 'Knee — inner (R)', view: 'front', shape: 'ellipse', cx: 105, cy: 287, rx: 6, ry: 9 },
		{ id: 'right_knee_front', label: 'Knee — front (R)', view: 'front', shape: 'circle', cx: 116, cy: 287, r: 7 },
		{ id: 'right_knee_outer', label: 'Knee — outer (R)', view: 'front', shape: 'ellipse', cx: 128, cy: 287, rx: 6, ry: 9 },

		// Shin
		{ id: 'left_shin_lateral', label: 'Shin — lateral / peroneal (L)', view: 'front', shape: 'rect', x: 70, y: 305, w: 8, h: 50, rx: 3 },
		{ id: 'left_shin_anterior', label: 'Shin — anterior tib (L)', view: 'front', shape: 'rect', x: 78, y: 305, w: 14, h: 50, rx: 5 },
		{ id: 'right_shin_anterior', label: 'Shin — anterior tib (R)', view: 'front', shape: 'rect', x: 108, y: 305, w: 14, h: 50, rx: 5 },
		{ id: 'right_shin_lateral', label: 'Shin — lateral / peroneal (R)', view: 'front', shape: 'rect', x: 122, y: 305, w: 8, h: 50, rx: 3 },

		// Foot
		{ id: 'left_ankle', label: 'Ankle (L)', view: 'front', shape: 'ellipse', cx: 84, cy: 372, rx: 9, ry: 6 },
		{ id: 'right_ankle', label: 'Ankle (R)', view: 'front', shape: 'ellipse', cx: 116, cy: 372, rx: 9, ry: 6 },
		{ id: 'left_foot_top', label: 'Foot — top (L)', view: 'front', shape: 'ellipse', cx: 78, cy: 392, rx: 11, ry: 5 },
		{ id: 'right_foot_top', label: 'Foot — top (R)', view: 'front', shape: 'ellipse', cx: 122, cy: 392, rx: 11, ry: 5 }
	];

	const BACK_REGIONS: Region[] = [
		// Upper back — traps (shoulders) + rhomboids/mid back
		{ id: 'left_upper_trap', label: 'Upper trap (L)', view: 'back', shape: 'rect', x: 66, y: 58, w: 26, h: 24, rx: 6 },
		{ id: 'right_upper_trap', label: 'Upper trap (R)', view: 'back', shape: 'rect', x: 108, y: 58, w: 26, h: 24, rx: 6 },
		{ id: 'left_mid_back', label: 'Mid back / rhomboid (L)', view: 'back', shape: 'rect', x: 72, y: 86, w: 20, h: 48, rx: 5 },
		{ id: 'mid_back_center', label: 'Mid back — center / thoracic spine', view: 'back', shape: 'rect', x: 92, y: 86, w: 16, h: 48, rx: 5 },
		{ id: 'right_mid_back', label: 'Mid back / rhomboid (R)', view: 'back', shape: 'rect', x: 108, y: 86, w: 20, h: 48, rx: 5 },

		// Low back
		{ id: 'left_low_back', label: 'Low back — left (QL)', view: 'back', shape: 'rect', x: 80, y: 138, w: 12, h: 32, rx: 4 },
		{ id: 'mid_low_back', label: 'Low back — center', view: 'back', shape: 'rect', x: 92, y: 138, w: 16, h: 32, rx: 4 },
		{ id: 'right_low_back', label: 'Low back — right (QL)', view: 'back', shape: 'rect', x: 108, y: 138, w: 12, h: 32, rx: 4 },

		// Glutes
		{ id: 'left_glute_med', label: 'Glute med (L)', view: 'back', shape: 'ellipse', cx: 72, cy: 178, rx: 8, ry: 9 },
		{ id: 'left_glute_max', label: 'Glute max (L)', view: 'back', shape: 'ellipse', cx: 86, cy: 192, rx: 12, ry: 14 },
		{ id: 'right_glute_med', label: 'Glute med (R)', view: 'back', shape: 'ellipse', cx: 128, cy: 178, rx: 8, ry: 9 },
		{ id: 'right_glute_max', label: 'Glute max (R)', view: 'back', shape: 'ellipse', cx: 114, cy: 192, rx: 12, ry: 14 },

		// Hamstrings
		{ id: 'left_ham_upper', label: 'Upper hamstring (L)', view: 'back', shape: 'rect', x: 72, y: 210, w: 22, h: 22, rx: 6 },
		{ id: 'left_ham_mid', label: 'Mid hamstring (L)', view: 'back', shape: 'rect', x: 72, y: 232, w: 22, h: 22, rx: 6 },
		{ id: 'left_ham_lower', label: 'Lower hamstring (L)', view: 'back', shape: 'rect', x: 72, y: 254, w: 22, h: 22, rx: 6 },
		{ id: 'right_ham_upper', label: 'Upper hamstring (R)', view: 'back', shape: 'rect', x: 106, y: 210, w: 22, h: 22, rx: 6 },
		{ id: 'right_ham_mid', label: 'Mid hamstring (R)', view: 'back', shape: 'rect', x: 106, y: 232, w: 22, h: 22, rx: 6 },
		{ id: 'right_ham_lower', label: 'Lower hamstring (R)', view: 'back', shape: 'rect', x: 106, y: 254, w: 22, h: 22, rx: 6 },

		// IT band
		{ id: 'left_itb_upper', label: 'IT band — upper (L)', view: 'back', shape: 'rect', x: 65, y: 215, w: 6, h: 30, rx: 3 },
		{ id: 'left_itb_lower', label: 'IT band — lower (L)', view: 'back', shape: 'rect', x: 65, y: 245, w: 6, h: 30, rx: 3 },
		{ id: 'right_itb_upper', label: 'IT band — upper (R)', view: 'back', shape: 'rect', x: 129, y: 215, w: 6, h: 30, rx: 3 },
		{ id: 'right_itb_lower', label: 'IT band — lower (R)', view: 'back', shape: 'rect', x: 129, y: 245, w: 6, h: 30, rx: 3 },

		// Back of knee
		{ id: 'left_knee_back', label: 'Back of knee — popliteal (L)', view: 'back', shape: 'circle', cx: 84, cy: 287, r: 8 },
		{ id: 'right_knee_back', label: 'Back of knee — popliteal (R)', view: 'back', shape: 'circle', cx: 116, cy: 287, r: 8 },

		// Calf
		{ id: 'left_calf_upper_lat', label: 'Upper calf — lateral gastroc (L)', view: 'back', shape: 'rect', x: 74, y: 305, w: 10, h: 22, rx: 4 },
		{ id: 'left_calf_upper_med', label: 'Upper calf — medial gastroc (L)', view: 'back', shape: 'rect', x: 84, y: 305, w: 10, h: 22, rx: 4 },
		{ id: 'left_calf_lower', label: 'Lower calf / soleus (L)', view: 'back', shape: 'rect', x: 76, y: 327, w: 16, h: 28, rx: 4 },
		{ id: 'right_calf_upper_med', label: 'Upper calf — medial gastroc (R)', view: 'back', shape: 'rect', x: 106, y: 305, w: 10, h: 22, rx: 4 },
		{ id: 'right_calf_upper_lat', label: 'Upper calf — lateral gastroc (R)', view: 'back', shape: 'rect', x: 116, y: 305, w: 10, h: 22, rx: 4 },
		{ id: 'right_calf_lower', label: 'Lower calf / soleus (R)', view: 'back', shape: 'rect', x: 108, y: 327, w: 16, h: 28, rx: 4 },

		// Achilles
		{ id: 'left_achilles', label: 'Achilles (L)', view: 'back', shape: 'rect', x: 80, y: 358, w: 8, h: 18, rx: 3 },
		{ id: 'right_achilles', label: 'Achilles (R)', view: 'back', shape: 'rect', x: 112, y: 358, w: 8, h: 18, rx: 3 },

		// Heel + arch
		{ id: 'left_heel', label: 'Heel (L)', view: 'back', shape: 'ellipse', cx: 71, cy: 394, rx: 7, ry: 5 },
		{ id: 'left_arch', label: 'Arch / plantar (L)', view: 'back', shape: 'ellipse', cx: 85, cy: 394, rx: 7, ry: 5 },
		{ id: 'right_heel', label: 'Heel (R)', view: 'back', shape: 'ellipse', cx: 129, cy: 394, rx: 7, ry: 5 },
		{ id: 'right_arch', label: 'Arch / plantar (R)', view: 'back', shape: 'ellipse', cx: 115, cy: 394, rx: 7, ry: 5 }
	];

	const REGIONS: Region[] = [...FRONT_REGIONS, ...BACK_REGIONS];

	const REGION_LABELS: Record<string, string> = Object.fromEntries(
		REGIONS.map((r) => [r.id, r.label])
	);

	let visibleRegions = $derived(REGIONS.filter((r) => r.view === view));

	function fillFor(region: string): string {
		if (working.has(region)) return 'fill-rose-500/70';
		if (highlightedRegions.includes(region)) return 'fill-amber-400/50';
		if (region === hoveredRegion) return 'fill-sky-400/40';
		return 'fill-slate-600/30';
	}

	function strokeFor(region: string): string {
		if (working.has(region)) return 'stroke-rose-300';
		if (highlightedRegions.includes(region)) return 'stroke-amber-300';
		return 'stroke-slate-500/60';
	}

	function applyPaint(region: string) {
		const has = working.has(region);
		let next: Set<string> | null = null;
		if (paintMode === 'add' && !has) {
			next = new Set(working);
			next.add(region);
		} else if (paintMode === 'remove' && has) {
			next = new Set(working);
			next.delete(region);
		}
		if (next) {
			working = next;
			onRegionsChange?.(Array.from(next));
		}
	}

	function handleDown(region: string, e: PointerEvent) {
		const target = e.target as Element | null;
		try {
			target?.releasePointerCapture?.(e.pointerId);
		} catch {
			// no-op
		}
		paintMode = working.has(region) ? 'remove' : 'add';
		painting = true;
		applyPaint(region);
	}

	function handleEnter(region: string) {
		hoveredRegion = region;
		if (painting) applyPaint(region);
	}

	function onSvgPointerMove(e: PointerEvent) {
		if (!painting) return;
		const el = document.elementFromPoint(e.clientX, e.clientY) as Element | null;
		const region = el?.getAttribute?.('data-region');
		if (region && region in REGION_LABELS) {
			applyPaint(region);
		}
	}

	function endPaint() {
		painting = false;
	}

	const VIEW_LABELS: Record<View, string> = {
		front: 'Front',
		back: 'Back'
	};
</script>

<svelte:window onpointerup={endPaint} onpointercancel={endPaint} />

<div class="h-full w-full flex flex-col items-center bg-gray-950 p-2">
	<!-- View label + hover label combined -->
	<div class="flex items-baseline gap-3 w-full mb-1 px-1">
		<div class="text-xs uppercase tracking-wide font-semibold text-slate-400">
			{VIEW_LABELS[view]}
		</div>
		<div class="text-xs text-slate-300 font-medium truncate">
			{hoveredRegion ? REGION_LABELS[hoveredRegion] : ''}
		</div>
	</div>

	<!-- Body SVG -->
	<svg
		viewBox="0 0 200 420"
		class="flex-1 min-h-0 max-h-full select-none"
		style="touch-action: none"
		role="img"
		aria-label="Body diagram for selecting an area of pain or tightness"
		onpointermove={onSvgPointerMove}
	>
		<!-- Body silhouette (always non-interactive). -->
		<g class="pointer-events-none">
			<circle cx="100" cy="28" r="18" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<path d="M 92 44 L 92 56 L 108 56 L 108 44 Z" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<path
				d="M 70 56 Q 60 60 60 80 L 62 160 Q 62 170 70 172 L 130 172 Q 138 170 138 160 L 140 80 Q 140 60 130 56 Z"
				class="fill-slate-800/50 stroke-slate-600"
				stroke-width="1"
			/>
			<path d="M 60 62 Q 48 70 46 110 L 50 160 Q 52 170 56 168 L 60 130 Q 62 95 64 75 Z" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<path d="M 140 62 Q 152 70 154 110 L 150 160 Q 148 170 144 168 L 140 130 Q 138 95 136 75 Z" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<path d="M 64 172 Q 60 184 65 196 L 100 200 L 135 196 Q 140 184 136 172 Z" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<path
				d="M 65 196 Q 60 220 64 270 Q 66 310 72 360 Q 74 380 86 380 Q 92 360 92 320 Q 94 270 96 220 Q 98 200 100 200 Z"
				class="fill-slate-800/50 stroke-slate-600"
				stroke-width="1"
			/>
			<path
				d="M 135 196 Q 140 220 136 270 Q 134 310 128 360 Q 126 380 114 380 Q 108 360 108 320 Q 106 270 104 220 Q 102 200 100 200 Z"
				class="fill-slate-800/50 stroke-slate-600"
				stroke-width="1"
			/>
			<ellipse cx="78" cy="392" rx="14" ry="8" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
			<ellipse cx="122" cy="392" rx="14" ry="8" class="fill-slate-800/50 stroke-slate-600" stroke-width="1" />
		</g>

		<!-- Clickable regions -->
		<g>
			{#each visibleRegions as region (region.id)}
				{#if region.shape === 'rect'}
					<rect
						x={region.x}
						y={region.y}
						width={region.w}
						height={region.h}
						rx={region.rx ?? 0}
						class="cursor-pointer transition-colors {fillFor(region.id)} {strokeFor(region.id)}"
						stroke-width="1.5"
						data-region={region.id}
						onpointerdown={(e) => handleDown(region.id, e)}
						onpointerenter={() => handleEnter(region.id)}
						onpointerleave={() => (hoveredRegion = null)}
						role="button"
						tabindex="0"
						aria-label={region.label}
					/>
				{:else if region.shape === 'ellipse'}
					<ellipse
						cx={region.cx}
						cy={region.cy}
						rx={region.rx}
						ry={region.ry}
						class="cursor-pointer transition-colors {fillFor(region.id)} {strokeFor(region.id)}"
						stroke-width="1.5"
						data-region={region.id}
						onpointerdown={(e) => handleDown(region.id, e)}
						onpointerenter={() => handleEnter(region.id)}
						onpointerleave={() => (hoveredRegion = null)}
						role="button"
						tabindex="0"
						aria-label={region.label}
					/>
				{:else if region.shape === 'circle'}
					<circle
						cx={region.cx}
						cy={region.cy}
						r={region.r}
						class="cursor-pointer transition-colors {fillFor(region.id)} {strokeFor(region.id)}"
						stroke-width="1.5"
						data-region={region.id}
						onpointerdown={(e) => handleDown(region.id, e)}
						onpointerenter={() => handleEnter(region.id)}
						onpointerleave={() => (hoveredRegion = null)}
						role="button"
						tabindex="0"
						aria-label={region.label}
					/>
				{/if}
			{/each}
		</g>
	</svg>
</div>
