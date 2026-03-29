<script lang="ts">
	type Week = {
		start_date: string;
		week_number: number | null;
		planned_km: number;
		actual_km: number;
		focus: string;
		is_current: boolean;
		run_count: number;
	};

	let {
		weeks,
		selectedWeek,
		onSelectWeek
	}: {
		weeks: Week[];
		selectedWeek: string | null;
		onSelectWeek: (startDate: string) => void;
	} = $props();

	// Round max up to a nice number for the Y axis
	let rawMax = $derived(
		Math.max(...weeks.map(w => Math.max(w.actual_km, w.planned_km)), 1)
	);
	let yMax = $derived(Math.ceil(rawMax / 20) * 20);
	let yTicks = $derived(
		Array.from({ length: Math.floor(yMax / 20) + 1 }, (_, i) => i * 20)
	);

	function barHeight(km: number): string {
		return `${(km / yMax) * 100}%`;
	}

	function actualBarColor(week: Week): string {
		if (week.actual_km === 0) return 'bg-slate-700';
		if (week.planned_km <= 0) return 'bg-blue-500';
		const ratio = week.actual_km / week.planned_km;
		if (ratio >= 0.9) return 'bg-emerald-500';
		if (ratio >= 0.7) return 'bg-amber-500';
		return 'bg-red-500';
	}

	function shortLabel(week: Week): string {
		if (week.week_number) return `W${week.week_number}`;
		const d = new Date(week.start_date + 'T00:00:00');
		return d.toLocaleDateString('en', { month: 'short' }).slice(0, 3);
	}
</script>

<div class="p-3">
	<h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Plan Overview</h2>

	<!-- Bar chart with Y axis -->
	<div class="flex h-40">
		<!-- Y axis labels -->
		<div class="flex flex-col justify-between items-end pr-1.5 shrink-0 relative" style="padding-bottom: 18px;">
			{#each [...yTicks].reverse() as tick}
				<span class="text-[9px] tabular-nums text-slate-600 leading-none">{tick}</span>
			{/each}
		</div>

		<!-- Chart area -->
		<div class="flex-1 flex items-end gap-[3px] relative border-l border-slate-800">
			<!-- Horizontal grid lines -->
			{#each yTicks as tick}
				{#if tick > 0}
					<div
						class="absolute left-0 right-0 border-t border-slate-800/60 pointer-events-none"
						style="bottom: calc({(tick / yMax) * 100}% + 18px)"
					></div>
				{/if}
			{/each}

			{#each weeks as week}
				<button
					class="flex flex-col items-center flex-1 min-w-0 h-full group cursor-pointer"
					onclick={() => onSelectWeek(week.start_date)}
					title="{week.actual_km.toFixed(0)}km actual{week.planned_km > 0 ? ` / ${week.planned_km}km planned` : ''}"
				>
					<!-- Bar area -->
					<div class="w-full flex-1 relative">
						<!-- Planned bar (wide, grey) -->
						{#if week.planned_km > 0}
							<div
								class="absolute bottom-0 left-0 right-0 rounded-t bg-slate-700/50"
								style="height: {barHeight(week.planned_km)}"
							></div>
						{/if}

						<!-- Actual bar (narrower, colored, in front) -->
						<div
							class="absolute bottom-0 rounded-t transition-all duration-300 z-10
								{actualBarColor(week)}
								{selectedWeek === week.start_date ? 'ring-1 ring-white/30' : ''}"
							style="height: {barHeight(week.actual_km)}; left: 15%; right: 15%;"
						></div>
					</div>

					<!-- Week label -->
					<span class="text-[9px] mt-1 tabular-nums leading-tight shrink-0
						{week.is_current ? 'text-emerald-400 font-bold' : selectedWeek === week.start_date ? 'text-slate-200' : 'text-slate-500'}">
						{shortLabel(week)}
					</span>

					{#if week.is_current}
						<div class="w-1 h-1 rounded-full bg-emerald-400 mt-0.5 shrink-0"></div>
					{/if}
				</button>
			{/each}
		</div>
	</div>

	<!-- Legend -->
	<div class="flex items-center gap-4 mt-2 text-[10px] text-slate-500">
		<span class="flex items-center gap-1">
			<span class="w-2 h-2 rounded-sm bg-emerald-500 inline-block"></span> Actual
		</span>
		<span class="flex items-center gap-1">
			<span class="w-2 h-2 rounded-sm bg-slate-700/50 inline-block"></span> Planned
		</span>
	</div>
</div>
