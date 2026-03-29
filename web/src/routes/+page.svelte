<script lang="ts">
	import { onMount } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';

	let terminalEl: HTMLDivElement;

	onMount(() => {
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

		const fitAddon = new FitAddon();
		term.loadAddon(fitAddon);
		term.loadAddon(new WebLinksAddon());

		term.open(terminalEl);
		fitAddon.fit();

		// Connect WebSocket
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
		ws.binaryType = 'arraybuffer';

		ws.onopen = () => {
			// Send initial size
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

		// Terminal input -> WebSocket
		term.onData((data) => {
			if (ws.readyState === WebSocket.OPEN) {
				ws.send(data);
			}
		});

		// Handle resize
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

<div bind:this={terminalEl} class="h-screen w-screen"></div>
