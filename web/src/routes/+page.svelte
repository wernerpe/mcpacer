<script lang="ts">
	import { onMount } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';
	import PlanOverview from '$lib/PlanOverview.svelte';
	import WeekDetail from '$lib/WeekDetail.svelte';
	import RunDetail from '$lib/RunDetail.svelte';

	let terminalEl: HTMLDivElement;
	let fitAddon: FitAddon;

	// Data state
	let weeks: any[] = $state([]);
	let selectedWeek: string | null = $state(null);
	let weekData: any = $state(null);
	let runData: any = $state(null);
	let runLoading: boolean = $state(false);

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

	onMount(() => {
		// Load data
		loadWeeks();

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

		// Connect WebSocket
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
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
			term.write('\r\n\x1b[90m[Session ended. Refresh to reconnect.]\x1b[0m\r\n');
		};

		term.onData((data) => {
			if (ws.readyState === WebSocket.OPEN) {
				ws.send(data);
			}
		});

		const handleResize = () => {
			fitAddon.fit();
			if (ws.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }));
			}
		};

		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
			ws.close();
			term.dispose();
		};
	});
</script>

<div class="h-screen w-screen flex flex-col bg-gray-950">
	<!-- Top: panels -->
	<div class="flex flex-1 min-h-0 border-b border-slate-800">
		<!-- Left sidebar: plan + week -->
		<div class="w-96 flex flex-col border-r border-slate-800 shrink-0">
			<!-- Plan overview (top half) -->
			<div class="flex-1 min-h-0 overflow-y-auto border-b border-slate-800">
				<PlanOverview {weeks} {selectedWeek} onSelectWeek={selectWeek} />
			</div>
			<!-- Week detail (bottom half) -->
			<div class="flex-1 min-h-0 overflow-y-auto">
				<WeekDetail {weekData} onSelectRun={selectRun} />
			</div>
		</div>

		<!-- Right: run detail -->
		<div class="flex-1 min-h-0">
			<RunDetail {runData} loading={runLoading} />
		</div>
	</div>

	<!-- Bottom: terminal -->
	<div class="h-80 shrink-0">
		<div bind:this={terminalEl} class="h-full w-full"></div>
	</div>
</div>
