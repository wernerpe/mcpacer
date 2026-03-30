<script lang="ts">
	import { onMount } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';
	import PlanOverview from '$lib/PlanOverview.svelte';
	import WeekDetail from '$lib/WeekDetail.svelte';
	import RunDetail from '$lib/RunDetail.svelte';
	import Onboarding from '$lib/Onboarding.svelte';

	let terminalEl: HTMLDivElement;
	let fitAddon: FitAddon;

	// Data state
	let weeks: any[] = $state([]);
	let selectedWeek: string | null = $state(null);
	let weekData: any = $state(null);
	let runData: any = $state(null);
	let runLoading: boolean = $state(false);
	let authChecked: boolean = $state(false);
	let stravaConnected: boolean = $state(false);

	// Panel sizes (pixels for sidebar/terminal, fraction for sidebar split)
	let sidebarWidth = $state(320); // 20rem = 320px
	let terminalHeight = $state(320); // h-80 = 20rem = 320px
	let sidebarSplit = $state(0.45); // fraction of sidebar height for plan overview

	// Drag state
	let dragging: 'sidebar' | 'terminal' | 'split' | null = $state(null);

	function onPointerDown(target: 'sidebar' | 'terminal' | 'split') {
		return (e: PointerEvent) => {
			e.preventDefault();
			dragging = target;
			(e.target as HTMLElement).setPointerCapture(e.pointerId);
		};
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging) return;

		if (dragging === 'sidebar') {
			sidebarWidth = Math.max(200, Math.min(e.clientX, window.innerWidth - 200));
		} else if (dragging === 'terminal') {
			const fromBottom = window.innerHeight - e.clientY;
			terminalHeight = Math.max(120, Math.min(fromBottom, window.innerHeight - 200));
			// Refit terminal after resize
			requestAnimationFrame(() => fitAddon?.fit());
		} else if (dragging === 'split') {
			const sidebar = document.getElementById('sidebar');
			if (sidebar) {
				const rect = sidebar.getBoundingClientRect();
				const relY = e.clientY - rect.top;
				sidebarSplit = Math.max(0.2, Math.min(relY / rect.height, 0.8));
			}
		}
	}

	function onPointerUp() {
		if (dragging === 'terminal' || dragging === 'sidebar') {
			// Refit terminal when done dragging
			requestAnimationFrame(() => fitAddon?.fit());
		}
		dragging = null;
	}

	async function loadWeeks() {
		const res = await fetch('/api/weeks');
		weeks = await res.json();
		// Auto-select current week
		const current = weeks.find((w: any) => w.is_current);
		if (current) selectWeek(current.start_date);
	}

	async function selectWeek(startDate: string) {
		selectedWeek = startDate;
		const res = await fetch(`/api/weeks/${startDate}`);
		weekData = await res.json();
	}

	async function selectRun(runId: number) {
		runLoading = true;
		try {
			const res = await fetch(`/api/runs/${runId}`);
			runData = await res.json();
		} finally {
			runLoading = false;
		}
	}

	function initDashboard() {
		loadWeeks();
		// Wait a tick for Svelte to render the terminal element
		requestAnimationFrame(() => initTerminal());
	}

	function initTerminal() {

		// Set up terminal
		const term = new Terminal({
			theme: {
				background: '#030712',
				foreground: '#e2e8f0',
				cursor: '#a78bfa',
				cursorAccent: '#030712',
				selectionBackground: '#334155',
				selectionForeground: '#e2e8f0',
				black: '#1e293b',
				red: '#f87171',
				green: '#4ade80',
				yellow: '#facc15',
				blue: '#60a5fa',
				magenta: '#c084fc',
				cyan: '#22d3ee',
				white: '#e2e8f0',
				brightBlack: '#475569',
				brightRed: '#fca5a5',
				brightGreen: '#86efac',
				brightYellow: '#fde68a',
				brightBlue: '#93c5fd',
				brightMagenta: '#d8b4fe',
				brightCyan: '#67e8f9',
				brightWhite: '#f8fafc'
			},
			fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
			fontSize: 14,
			lineHeight: 1.2,
			cursorBlink: true,
			cursorStyle: 'bar',
			allowProposedApi: true
		});

		fitAddon = new FitAddon();
		term.loadAddon(fitAddon);
		term.loadAddon(new WebLinksAddon());

		term.open(terminalEl);
		fitAddon.fit();

		// Connect WebSocket with auto-reconnect
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		let ws: WebSocket;
		let disposed = false;

		function connectWs() {
			ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
			ws.binaryType = 'arraybuffer';

			ws.onopen = () => {
				ws.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }));
			};

			ws.onmessage = (event) => {
				if (event.data instanceof ArrayBuffer) {
					term.write(new Uint8Array(event.data));
				} else {
					term.write(event.data);
				}
			};

			ws.onclose = () => {
				if (!disposed) {
					// Auto-reconnect after 1s
					setTimeout(connectWs, 1000);
				}
			};
		}

		connectWs();

		term.onData((data) => {
			if (ws?.readyState === WebSocket.OPEN) {
				ws.send(data);
			}
		});

		const handleResize = () => {
			fitAddon.fit();
			if (ws?.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }));
			}
		};

		window.addEventListener('resize', handleResize);

		return () => {
			disposed = true;
			window.removeEventListener('resize', handleResize);
			ws?.close();
			term.dispose();
		};
	}

	onMount(async () => {
		// Check if Strava is connected
		try {
			const res = await fetch('/auth/status');
			const status = await res.json();
			stravaConnected = status.connected;
		} catch {
			stravaConnected = false;
		}
		authChecked = true;

		if (stravaConnected) {
			initDashboard();
		}
	});
</script>

{#if !authChecked}
	<!-- Loading auth status -->
	<div class="h-screen w-screen bg-gray-950 flex items-center justify-center">
		<div class="text-slate-600 text-sm">Loading...</div>
	</div>
{:else if !stravaConnected}
	<Onboarding onConnected={() => { stravaConnected = true; initDashboard(); }} />
{:else}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="h-screen w-screen flex flex-col bg-gray-950"
		class:select-none={!!dragging}
		onpointermove={onPointerMove}
		onpointerup={onPointerUp}
	>
		<!-- Top: panels -->
		<div class="flex flex-1 min-h-0">
			<!-- Left sidebar: plan + week -->
			<div id="sidebar" class="flex flex-col shrink-0" style="width: {sidebarWidth}px">
				<!-- Plan overview -->
				<div class="min-h-0 overflow-y-auto" style="height: {sidebarSplit * 100}%">
					<PlanOverview {weeks} {selectedWeek} onSelectWeek={selectWeek} />
				</div>

				<!-- Horizontal drag handle: plan/week split -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="h-1 shrink-0 cursor-row-resize group flex items-center justify-center hover:bg-sky-500/30 transition-colors {dragging === 'split' ? 'bg-sky-500/30' : ''}"
					onpointerdown={onPointerDown('split')}
				>
					<div class="w-8 h-[2px] rounded bg-slate-700 group-hover:bg-sky-500/60 transition-colors"></div>
				</div>

				<!-- Week detail -->
				<div class="flex-1 min-h-0 overflow-y-auto">
					<WeekDetail {weekData} onSelectRun={selectRun} />
				</div>
			</div>

			<!-- Vertical drag handle: sidebar/main split -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="w-1 shrink-0 cursor-col-resize group flex items-center justify-center hover:bg-sky-500/30 transition-colors {dragging === 'sidebar' ? 'bg-sky-500/30' : ''}"
				onpointerdown={onPointerDown('sidebar')}
			>
				<div class="h-8 w-[2px] rounded bg-slate-700 group-hover:bg-sky-500/60 transition-colors"></div>
			</div>

			<!-- Right: run detail -->
			<div class="flex-1 min-h-0">
				<RunDetail {runData} loading={runLoading} />
			</div>
		</div>

		<!-- Horizontal drag handle: panels/terminal split -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="h-1 shrink-0 cursor-row-resize group flex items-center justify-center hover:bg-sky-500/30 transition-colors {dragging === 'terminal' ? 'bg-sky-500/30' : ''}"
			onpointerdown={onPointerDown('terminal')}
		>
			<div class="w-8 h-[2px] rounded bg-slate-700 group-hover:bg-sky-500/60 transition-colors"></div>
		</div>

		<!-- Bottom: terminal -->
		<div class="shrink-0 flex flex-col" style="height: {terminalHeight}px">
			<div class="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wide border-b border-slate-800 shrink-0">Coach</div>
			<div bind:this={terminalEl} class="flex-1 min-h-0 w-full"></div>
		</div>
	</div>
{/if}
