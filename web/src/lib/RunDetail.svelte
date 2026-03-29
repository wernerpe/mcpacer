<script lang="ts">
	import { onMount } from 'svelte';
	import L from 'leaflet';
	import 'leaflet/dist/leaflet.css';
	import polyline from '@mapbox/polyline';

	type Lap = {
		index: number;
		name: string;
		distance_km: number;
		moving_time_seconds: number;
		pace: string | null;
		avg_hr: number | null;
		max_hr: number | null;
		elevation_gain: number;
		avg_cadence: number | null;
	};

	type RunData = {
		id: number;
		name: string;
		date: string;
		distance_km: number;
		duration_seconds: number;
		elapsed_time_seconds: number;
		pace: string | null;
		avg_hr: number | null;
		max_hr: number | null;
		elevation_gain: number;
		digest: string | null;
		coach_notes: string[];
		laps: Lap[];
		summary_polyline: string | null;
	};

	let {
		runData,
		loading
	}: {
		runData: RunData | null;
		loading: boolean;
	} = $props();

	let mapEl: HTMLDivElement;
	let map: L.Map | null = null;

	function destroyMap() {
		if (map) {
			map.remove();
			map = null;
		}
	}

	function renderMap(poly: string) {
		destroyMap();

		const coords = polyline.decode(poly);
		const latLngs = coords.map(([lat, lng]: [number, number]) => L.latLng(lat, lng));

		map = L.map(mapEl, {
			zoomControl: false,
			attributionControl: false,
		});
		L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
			maxZoom: 19,
		}).addTo(map);

		const route = L.polyline(latLngs, {
			color: '#4ade80',
			weight: 3,
			opacity: 0.9,
		}).addTo(map);

		map.fitBounds(route.getBounds(), { padding: [20, 20] });
	}

	$effect(() => {
		if (runData?.summary_polyline && mapEl) {
			setTimeout(() => renderMap(runData!.summary_polyline!), 50);
		}
		return () => destroyMap();
	});

	function formatDuration(seconds: number): string {
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		const s = seconds % 60;
		if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function formatDate(dateStr: string): string {
		const d = new Date(dateStr);
		return d.toLocaleDateString('en', { weekday: 'short', month: 'short', day: 'numeric' });
	}

	function paceToSeconds(pace: string): number {
		const [m, s] = pace.split(':').map(Number);
		return m * 60 + s;
	}

	let maxLapPaceSec = $derived(
		runData?.laps
			? Math.max(...runData.laps.filter(l => l.pace).map(l => paceToSeconds(l.pace!)))
			: 0
	);

	let minLapPaceSec = $derived(
		runData?.laps
			? Math.min(...runData.laps.filter(l => l.pace).map(l => paceToSeconds(l.pace!)))
			: 0
	);

	function paceBarWidth(pace: string): string {
		const sec = paceToSeconds(pace);
		if (maxLapPaceSec === minLapPaceSec) return '80%';
		const range = maxLapPaceSec - minLapPaceSec;
		const normalized = 1 - (sec - minLapPaceSec) / range;
		return `${30 + normalized * 60}%`;
	}

	function paceBarColor(pace: string): string {
		const sec = paceToSeconds(pace);
		if (maxLapPaceSec === minLapPaceSec) return 'bg-blue-500';
		const range = maxLapPaceSec - minLapPaceSec;
		const normalized = 1 - (sec - minLapPaceSec) / range;
		if (normalized > 0.7) return 'bg-emerald-500';
		if (normalized > 0.3) return 'bg-blue-500';
		return 'bg-slate-500';
	}
</script>

{#if loading}
	<div class="flex items-center justify-center h-full text-slate-500 text-sm">
		Loading...
	</div>
{:else if runData}
	<div class="h-full overflow-y-auto p-4">
		<!-- Header -->
		<div class="mb-4">
			<h2 class="text-lg font-semibold text-slate-100">{runData.name}</h2>
			<p class="text-xs text-slate-500 mt-0.5">{formatDate(runData.date)}</p>
		</div>

		<!-- GPS Map -->
		{#if runData.summary_polyline}
			<div class="mb-4 rounded overflow-hidden border border-slate-700/50">
				<div bind:this={mapEl} class="h-48 w-full"></div>
			</div>
		{/if}

		<!-- Stats grid -->
		<div class="grid grid-cols-4 gap-3 mb-5">
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Distance</p>
				<p class="text-lg font-semibold text-slate-100 tabular-nums">{runData.distance_km}<span class="text-xs text-slate-500 ml-0.5">km</span></p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Pace</p>
				<p class="text-lg font-semibold text-slate-100 tabular-nums">{runData.pace}<span class="text-xs text-slate-500 ml-0.5">/km</span></p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Duration</p>
				<p class="text-lg font-semibold text-slate-100 tabular-nums">{formatDuration(runData.duration_seconds)}</p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Elev Gain</p>
				<p class="text-lg font-semibold text-slate-100 tabular-nums">{runData.elevation_gain}<span class="text-xs text-slate-500 ml-0.5">m</span></p>
			</div>
		</div>

		<!-- HR stats -->
		{#if runData.avg_hr}
			<div class="flex gap-6 mb-5 text-sm">
				<div>
					<span class="text-slate-500">Avg HR</span>
					<span class="text-red-400 ml-1.5 tabular-nums">{runData.avg_hr}</span>
					<span class="text-slate-600 text-xs">bpm</span>
				</div>
				{#if runData.max_hr}
					<div>
						<span class="text-slate-500">Max HR</span>
						<span class="text-red-400 ml-1.5 tabular-nums">{runData.max_hr}</span>
						<span class="text-slate-600 text-xs">bpm</span>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Digest -->
		{#if runData.digest}
			<div class="mb-5 px-3 py-2 bg-slate-800/50 rounded border border-slate-700/50">
				<p class="text-xs text-slate-400 font-mono">{runData.digest}</p>
			</div>
		{/if}

		<!-- Coach notes -->
		{#if runData.coach_notes.length > 0}
			<div class="mb-5">
				<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Coach Notes</h3>
				{#each runData.coach_notes as note}
					<p class="text-xs text-slate-300 mb-1 pl-3 border-l-2 border-amber-500/50">{note}</p>
				{/each}
			</div>
		{/if}

		<!-- Lap splits -->
		{#if runData.laps.length > 1}
			<div>
				<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
					Lap Splits
					<span class="text-slate-600 font-normal ml-1">({runData.laps.length})</span>
				</h3>

				<div class="flex flex-col gap-[2px]">
					{#each runData.laps as lap}
						<div class="flex items-center gap-2 text-xs py-1 px-2 rounded hover:bg-slate-800/50 group">
							<span class="w-5 text-right text-slate-600 tabular-nums shrink-0">{lap.index}</span>

							<div class="flex-1 min-w-0 relative h-5 flex items-center">
								{#if lap.pace}
									<div
										class="h-full rounded {paceBarColor(lap.pace)} opacity-20 absolute left-0"
										style="width: {paceBarWidth(lap.pace)}"
									></div>
									<span class="relative z-10 text-slate-200 tabular-nums ml-1">{lap.pace}/km</span>
								{/if}
							</div>

							<span class="w-14 text-right text-slate-400 tabular-nums shrink-0">{lap.distance_km}km</span>

							<span class="w-10 text-right tabular-nums shrink-0
								{lap.avg_hr ? 'text-red-400/70' : 'text-slate-700'}">
								{lap.avg_hr ?? '—'}
							</span>

							{#if lap.elevation_gain > 0}
								<span class="w-10 text-right text-slate-600 tabular-nums shrink-0">+{lap.elevation_gain}m</span>
							{:else}
								<span class="w-10 shrink-0"></span>
							{/if}
						</div>
					{/each}
				</div>

				<div class="flex items-center gap-2 text-[9px] text-slate-600 px-2 mt-1 border-t border-slate-800/50 pt-1">
					<span class="w-5"></span>
					<span class="flex-1">pace</span>
					<span class="w-14 text-right">dist</span>
					<span class="w-10 text-right">hr</span>
					<span class="w-10 text-right">elev</span>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center h-full text-slate-600 text-sm">
		<div class="text-center">
			<p class="text-lg mb-1">Click a run to view details</p>
			<p class="text-xs text-slate-700">Lap splits, pace, HR, GPS track</p>
		</div>
	</div>
{/if}
