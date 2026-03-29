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

	function secondsToPace(sec: number): string {
		const m = Math.floor(sec / 60);
		const s = Math.round(sec % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	// For the vertical bar chart: pace Y axis (inverted — faster = taller)
	let paceLaps = $derived(
		runData?.laps?.filter(l => l.pace) ?? []
	);

	let maxPaceSec = $derived(
		paceLaps.length ? Math.max(...paceLaps.map(l => paceToSeconds(l.pace!))) : 0
	);

	let minPaceSec = $derived(
		paceLaps.length ? Math.min(...paceLaps.map(l => paceToSeconds(l.pace!))) : 0
	);

	// Total duration for proportional widths
	let totalDuration = $derived(
		paceLaps.reduce((sum, l) => sum + (l.moving_time_seconds || 0), 0)
	);

	function lapWidthPct(lap: Lap): string {
		if (totalDuration === 0) return `${100 / paceLaps.length}%`;
		return `${(lap.moving_time_seconds / totalDuration) * 100}%`;
	}

	// Y axis: round to nice pace values, add padding
	let yMaxSec = $derived(Math.ceil(maxPaceSec / 30) * 30 + 30);
	let yMinSec = $derived(Math.max(Math.floor(minPaceSec / 30) * 30 - 30, 0));
	let yRange = $derived(yMaxSec - yMinSec);

	// Generate Y axis ticks (every 30s or 60s depending on range)
	let tickInterval = $derived(yRange > 240 ? 60 : 30);
	let yTicks = $derived(
		Array.from(
			{ length: Math.floor(yRange / tickInterval) + 1 },
			(_, i) => yMinSec + i * tickInterval
		)
	);

	// Bar height: faster pace = taller (inverted scale)
	function lapBarHeight(pace: string): string {
		const sec = paceToSeconds(pace);
		const height = ((yMaxSec - sec) / yRange) * 100;
		return `${Math.max(height, 2)}%`;
	}

	// Bar color based on effort: faster = more intense color
	function lapBarColor(pace: string): string {
		if (maxPaceSec === minPaceSec) return 'bg-sky-500';
		const sec = paceToSeconds(pace);
		const range = maxPaceSec - minPaceSec;
		const intensity = 1 - (sec - minPaceSec) / range;
		if (intensity > 0.7) return 'bg-cyan-400';
		if (intensity > 0.3) return 'bg-sky-600';
		return 'bg-sky-900';
	}

	let hoveredLap = $state<number | null>(null);
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
		<div class="grid grid-cols-3 gap-x-4 gap-y-2 mb-4">
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Distance</p>
				<p class="text-base font-semibold text-slate-100 tabular-nums">{runData.distance_km}<span class="text-xs text-slate-500 ml-0.5">km</span></p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Pace</p>
				<p class="text-base font-semibold text-slate-100 tabular-nums">{runData.pace}<span class="text-xs text-slate-500 ml-0.5">/km</span></p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Duration</p>
				<p class="text-base font-semibold text-slate-100 tabular-nums">{formatDuration(runData.duration_seconds)}</p>
			</div>
			<div>
				<p class="text-[10px] text-slate-500 uppercase tracking-wide">Elev Gain</p>
				<p class="text-base font-semibold text-slate-100 tabular-nums">{runData.elevation_gain}<span class="text-xs text-slate-500 ml-0.5">m</span></p>
			</div>
			{#if runData.avg_hr}
				<div>
					<p class="text-[10px] text-slate-500 uppercase tracking-wide">Avg HR</p>
					<p class="text-base font-semibold text-red-400 tabular-nums">{runData.avg_hr}<span class="text-xs text-slate-500 ml-0.5">bpm</span></p>
				</div>
			{/if}
			{#if runData.max_hr}
				<div>
					<p class="text-[10px] text-slate-500 uppercase tracking-wide">Max HR</p>
					<p class="text-base font-semibold text-red-400 tabular-nums">{runData.max_hr}<span class="text-xs text-slate-500 ml-0.5">bpm</span></p>
				</div>
			{/if}
		</div>

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

		<!-- Workout Analysis (lap splits as vertical bar chart) -->
		{#if runData.laps.length > 1}
			<div>
				<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
					Workout Analysis
					<span class="text-slate-600 font-normal ml-1">({runData.laps.length} laps)</span>
				</h3>

				<!-- Tooltip for hovered lap -->
				{#if hoveredLap !== null}
					{@const lap = runData.laps[hoveredLap]}
					<div class="mb-2 px-3 py-1.5 bg-slate-800 rounded border border-slate-700 text-[11px] tabular-nums">
						<span class="text-slate-200 font-medium">Lap {lap.index}</span>
						<span class="text-slate-500 ml-3">{lap.distance_km}km</span>
						{#if lap.pace}<span class="text-slate-200 ml-3">{lap.pace}/km</span>{/if}
						{#if lap.moving_time_seconds}<span class="text-slate-500 ml-3">{formatDuration(lap.moving_time_seconds)}</span>{/if}
						{#if lap.avg_hr}<span class="text-red-400 ml-3">HR {lap.avg_hr}</span>{/if}
					</div>
				{/if}

				<!-- Vertical bar chart — taller, touching bars, proportional widths -->
				<div class="flex h-48">
					<!-- Y axis (pace labels) -->
					<div class="flex flex-col justify-between items-end pr-2 shrink-0" style="padding-bottom: 18px;">
						{#each [...yTicks].reverse() as tick}
							<span class="text-[10px] tabular-nums text-slate-500 leading-none">{secondsToPace(tick)}</span>
						{/each}
					</div>

					<!-- Chart area -->
					<div class="flex-1 flex items-end relative border-l border-slate-700">
						<!-- Grid lines -->
						{#each yTicks as tick}
							{#if tick > yMinSec && tick < yMaxSec}
								<div
									class="absolute left-0 right-0 border-t border-slate-800/60 pointer-events-none z-0"
									style="bottom: calc({((tick - yMinSec) / yRange) * 100}% + 18px)"
								></div>
							{/if}
						{/each}

						<!-- Bars — proportional width, hairline gap -->
						{#each runData.laps as lap, i}
							{#if lap.pace}
								<button
									class="flex flex-col items-center min-w-0 h-full cursor-pointer shrink-0"
									style="width: calc({lapWidthPct(lap)} - 1px); margin-right: 1px"
									onmouseenter={() => hoveredLap = i}
									onmouseleave={() => hoveredLap = null}
								>
									<!-- Bar area -->
									<div class="w-full flex-1 relative">
										<div
											class="absolute bottom-0 left-0 right-0 transition-all duration-150
												{lapBarColor(lap.pace)}
												{hoveredLap === i ? 'opacity-100 brightness-125' : 'opacity-80'}"
											style="height: {lapBarHeight(lap.pace)}"
										></div>
									</div>

									<!-- Lap number (only show if bar is wide enough) -->
									<span class="text-[10px] mt-0.5 tabular-nums shrink-0 truncate
										{hoveredLap === i ? 'text-slate-200' : 'text-slate-600'}">
										{lap.index}
									</span>
								</button>
							{/if}
						{/each}
					</div>
				</div>

				<!-- Splits table -->
				<div class="mt-3 border-t border-slate-800/50 pt-2">
					<table class="w-full text-[11px] tabular-nums">
						<thead>
							<tr class="text-slate-500">
								<th class="text-right pr-3 py-1 font-normal w-8">#</th>
								<th class="text-left py-1 font-normal">Pace</th>
								<th class="text-right py-1 font-normal pr-3">Dist</th>
								<th class="text-right py-1 font-normal pr-3">Time</th>
								<th class="text-right py-1 font-normal pr-3">HR</th>
								<th class="text-right py-1 font-normal">Elev</th>
							</tr>
						</thead>
						<tbody>
							{#each runData.laps as lap, i}
								<tr class="border-t border-slate-800/30 transition-colors
									{hoveredLap === i ? 'bg-slate-800/50' : 'hover:bg-slate-800/30'}"
									onmouseenter={() => hoveredLap = i}
									onmouseleave={() => hoveredLap = null}
								>
									<td class="text-right pr-3 py-1 text-slate-500">{lap.index}</td>
									<td class="text-left py-1 text-slate-200">{lap.pace ?? '—'}/km</td>
									<td class="text-right py-1 pr-3 text-slate-400">{lap.distance_km}km</td>
									<td class="text-right py-1 pr-3 text-slate-500">{formatDuration(lap.moving_time_seconds)}</td>
									<td class="text-right py-1 pr-3 {lap.avg_hr ? 'text-red-400' : 'text-slate-700'}">{lap.avg_hr ?? '—'}</td>
									<td class="text-right py-1 text-slate-500">
										{lap.elevation_gain > 0 ? `+${lap.elevation_gain}m` : ''}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
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
