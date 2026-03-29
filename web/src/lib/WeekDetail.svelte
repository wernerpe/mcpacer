<script lang="ts">
	type PrescribedRun = {
		day: string;
		type: string;
		distance_km: number | null;
		description: string;
		structure: string | null;
		target_pace: string | null;
	};

	type ActualRun = {
		id: number;
		name: string;
		date: string;
		distance_km: number;
		duration_seconds: number;
		pace: string | null;
		avg_hr: number | null;
		digest: string | null;
	};

	type WeekData = {
		start_date: string;
		prescribed: PrescribedRun[];
		actual_by_day: Record<string, ActualRun[]>;
		actual_runs: ActualRun[];
	};

	let {
		weekData,
		onSelectRun
	}: {
		weekData: WeekData | null;
		onSelectRun: (runId: number) => void;
	} = $props();

	const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

	function formatDuration(seconds: number): string {
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}h${m.toString().padStart(2, '0')}m`;
		return `${m}m`;
	}

	function typeColor(type: string): string {
		switch (type) {
			case 'workout': return 'text-amber-400';
			case 'long_run': return 'text-blue-400';
			case 'race': return 'text-red-400';
			case 'easy': return 'text-emerald-400';
			case 'recovery': return 'text-slate-400';
			case 'shakeout': return 'text-slate-400';
			default: return 'text-slate-300';
		}
	}

	async function copyWeekPlan() {
		if (!weekData) return;
		const lines = weekData.prescribed.map(r => {
			const dist = r.distance_km ? `${r.distance_km}km` : '';
			const desc = r.structure || r.description;
			return `${r.day}: ${dist} ${desc}`.trim();
		});
		await navigator.clipboard.writeText(lines.join('\n'));
	}
</script>

{#if weekData}
	<div class="flex flex-col gap-1 p-3 overflow-y-auto">
		<div class="flex items-center justify-between mb-2">
			<h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wide">Week Detail</h2>
			<button
				class="text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-0.5 rounded hover:bg-slate-800"
				onclick={copyWeekPlan}
			>
				Copy
			</button>
		</div>

		{#each DAYS as day}
			{@const prescribed = weekData.prescribed.find(r => r.day === day)}
			{@const actuals = weekData.actual_by_day[day] || []}

			{#if prescribed || actuals.length > 0}
				<div class="flex items-start gap-2 px-2 py-1 text-xs rounded
					{actuals.length > 0 ? '' : 'opacity-60'}">
					<span class="w-8 text-slate-500 shrink-0">{day.slice(0, 3)}</span>

					<div class="flex-1 min-w-0">
						{#if actuals.length > 0}
							{#each actuals as run}
								<button
									class="block w-full text-left hover:bg-slate-800 rounded px-1 py-0.5 transition-colors"
									onclick={() => onSelectRun(run.id)}
								>
									<span class="text-slate-200">{run.distance_km}km</span>
									{#if run.pace}
										<span class="text-slate-400">{run.pace}/km</span>
									{/if}
									{#if run.avg_hr}
										<span class="text-slate-500">HR {Math.round(run.avg_hr)}</span>
									{/if}
								</button>
							{/each}
						{:else if prescribed}
							<span class={typeColor(prescribed.type)}>
								{#if prescribed.distance_km}{prescribed.distance_km}km{/if}
								{prescribed.description}
							</span>
						{/if}
					</div>

					<!-- Completion indicator -->
					<span class="shrink-0">
						{#if actuals.length > 0}
							<span class="text-emerald-400">✓</span>
						{:else if prescribed}
							<span class="text-slate-600">○</span>
						{/if}
					</span>
				</div>
			{/if}
		{/each}
	</div>
{:else}
	<div class="flex items-center justify-center h-full text-slate-600 text-sm">
		Select a week
	</div>
{/if}
