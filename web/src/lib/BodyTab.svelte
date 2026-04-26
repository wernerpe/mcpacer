<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import BodyViewer from './BodyViewer.svelte';

	let selectedRegions: string[] = $state([]);
	let highlightedRegions: string[] = $state([]);
	let highlightReason: string = $state('');

	let ws: WebSocket | null = null;
	let wsClosed = false;

	// Local guard: when our own POST returns and the broadcast comes back,
	// we don't want to overwrite a paint operation already in progress.
	let postInFlight = 0;

	async function postPainted(regions: string[]) {
		postInFlight++;
		try {
			await fetch('/api/body/painted', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ regions })
			});
		} catch (e) {
			console.warn('[body] paint POST failed', e);
		} finally {
			postInFlight--;
		}
	}

	function handleRegionsChange(regions: string[]) {
		selectedRegions = regions;
		postPainted(regions);
	}

	function clearAll() {
		handleRegionsChange([]);
	}

	function applyState(state: {
		painted?: string[];
		highlighted?: string[];
		highlight_reason?: string;
	}) {
		// Don't clobber the user's local paint while a POST is racing back.
		if (postInFlight === 0 && Array.isArray(state.painted)) {
			selectedRegions = state.painted;
		}
		if (Array.isArray(state.highlighted)) {
			highlightedRegions = state.highlighted;
		}
		highlightReason = state.highlight_reason ?? '';
	}

	async function loadInitialState() {
		try {
			const res = await fetch('/api/body/state');
			if (res.ok) applyState(await res.json());
		} catch (e) {
			console.warn('[body] initial state load failed', e);
		}
	}

	function connectWs() {
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
		ws.onmessage = (event) => {
			// /ws/events may carry plain "refresh" strings (legacy) or JSON
			// payloads with a `type` field. We only care about body_state.
			const data = event.data;
			if (typeof data !== 'string') return;
			try {
				const parsed = JSON.parse(data);
				if (parsed?.type === 'body_state' && parsed.state) {
					applyState(parsed.state);
				}
			} catch {
				// Non-JSON message ("refresh") — ignore.
			}
		};
		ws.onclose = () => {
			if (!wsClosed) setTimeout(connectWs, 2000);
		};
	}

	onMount(() => {
		loadInitialState();
		connectWs();
	});

	onDestroy(() => {
		wsClosed = true;
		ws?.close();
	});
</script>

<div class="h-full w-full flex flex-col bg-gray-950">
	<!-- Header bar -->
	<div class="px-4 py-2 border-b border-slate-800 flex items-center gap-3 shrink-0">
		<div class="text-xs text-slate-400 flex-1 truncate">
			Click or paint where it hurts — your coach can see what you've marked.
		</div>

		{#if highlightReason && highlightedRegions.length > 0}
			<div class="text-xs text-amber-300 italic truncate max-w-[40%]">
				🟡 {highlightReason}
			</div>
		{/if}

		{#if selectedRegions.length > 0}
			<div class="text-xs text-rose-300 font-medium">
				{selectedRegions.length} region{selectedRegions.length === 1 ? '' : 's'}
			</div>
		{/if}

		<button
			class="px-3 py-1 text-xs rounded transition-colors {selectedRegions.length > 0
				? 'bg-slate-800 text-slate-300 hover:bg-rose-900/50 hover:text-rose-200'
				: 'bg-slate-900 text-slate-600 cursor-not-allowed'}"
			disabled={selectedRegions.length === 0}
			onclick={clearAll}
		>
			Clear
		</button>
	</div>

	<!-- Two viewers side by side, always both visible -->
	<div class="flex-1 min-h-0 flex">
		<div class="w-1/2 min-w-0 border-r border-slate-800">
			<BodyViewer
				view="front"
				{selectedRegions}
				{highlightedRegions}
				onRegionsChange={handleRegionsChange}
			/>
		</div>
		<div class="w-1/2 min-w-0">
			<BodyViewer
				view="back"
				{selectedRegions}
				{highlightedRegions}
				onRegionsChange={handleRegionsChange}
			/>
		</div>
	</div>
</div>
