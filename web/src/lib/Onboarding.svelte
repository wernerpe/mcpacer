<script lang="ts">
	let {
		onConnected
	}: {
		onConnected: () => void;
	} = $props();

	let step: 'credentials' | 'waiting' | 'success' = $state('credentials');
	let clientId = $state('');
	let clientSecret = $state('');
	let error = $state('');
	let loading = $state(false);

	async function startOAuth() {
		if (!clientId.trim() || !clientSecret.trim()) {
			error = 'Both fields are required.';
			return;
		}

		error = '';
		loading = true;

		try {
			const res = await fetch('/auth/credentials', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ client_id: clientId.trim(), client_secret: clientSecret.trim() }),
			});

			if (!res.ok) {
				error = 'Failed to save credentials. Check the server.';
				loading = false;
				return;
			}

			const data = await res.json();
			step = 'waiting';

			// Listen for the callback message from the popup
			const handler = (event: MessageEvent) => {
				if (event.data === 'strava-auth-success') {
					window.removeEventListener('message', handler);
					step = 'success';
					setTimeout(() => onConnected(), 1200);
				}
			};
			window.addEventListener('message', handler);

			// Open Strava OAuth in a popup
			const popup = window.open(data.oauth_url, 'strava-auth', 'width=600,height=700');

			// Fallback: poll auth status in case popup message doesn't fire
			const poll = setInterval(async () => {
				try {
					const statusRes = await fetch('/auth/status');
					const status = await statusRes.json();
					if (status.connected) {
						clearInterval(poll);
						window.removeEventListener('message', handler);
						step = 'success';
						setTimeout(() => onConnected(), 1200);
					}
				} catch {}
			}, 2000);

			// Stop polling after 5 minutes
			setTimeout(() => clearInterval(poll), 300000);
		} catch (e) {
			error = 'Network error. Is the server running?';
			loading = false;
		}
	}
</script>

<div class="h-screen w-screen bg-gray-950 flex items-center justify-center">
	<div class="max-w-lg w-full mx-4">
		<!-- Logo / Title -->
		<div class="text-center mb-8">
			<div class="inline-flex items-center gap-2 mb-3">
				<div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-rose-600 flex items-center justify-center">
					<svg class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
					</svg>
				</div>
			</div>
			<h1 class="text-2xl font-bold text-slate-100">Strava Running Coach</h1>
			<p class="text-sm text-slate-500 mt-1">AI-powered coaching from your training data</p>
		</div>

		{#if step === 'credentials'}
			<!-- Step 1: Instructions + credential input -->
			<div class="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
				<h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-3">Step 1 — Create a Strava API App</h2>

				<div class="text-xs text-slate-400 space-y-2 mb-5">
					<p>Follow the instructions <a href="https://developers.strava.com/docs/getting-started/" target="_blank" rel="noopener" class="text-sky-400 hover:text-sky-300 underline underline-offset-2">here</a> (Section B) to register an app with your <a href="https://www.strava.com/settings/api" target="_blank" rel="noopener" class="text-sky-400 hover:text-sky-300 underline underline-offset-2">personal Strava API page</a>. Fill in the form with:</p>
					<div class="bg-slate-800/50 rounded p-3 font-mono space-y-1">
						<div><span class="text-slate-500">Application Name:</span> <span class="text-slate-200">My Strava Running Coach</span></div>
						<div><span class="text-slate-500">Category:</span> <span class="text-slate-200">Training / Analysis</span></div>
						<div><span class="text-slate-500">Website:</span> <span class="text-slate-200">http://localhost</span></div>
						<div><span class="text-slate-500">Authorization Callback Domain:</span> <span class="text-emerald-400">localhost</span></div>
					</div>
					<p>After creating the app, copy your <strong class="text-slate-300">Client ID</strong> and <strong class="text-slate-300">Client Secret</strong> below.</p>
				</div>

				<h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-3">Step 2 — Connect</h2>

				<div class="space-y-3">
					<div>
						<label for="client-id" class="block text-xs text-slate-500 mb-1">Client ID</label>
						<input
							id="client-id"
							type="text"
							bind:value={clientId}
							placeholder="e.g. 123456"
							class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/30 font-mono"
						/>
					</div>
					<div>
						<label for="client-secret" class="block text-xs text-slate-500 mb-1">Client Secret</label>
						<input
							id="client-secret"
							type="password"
							bind:value={clientSecret}
							placeholder="e.g. 0d72405f043cc635..."
							class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/30 font-mono"
						/>
					</div>

					{#if error}
						<p class="text-xs text-red-400">{error}</p>
					{/if}

					<button
						onclick={startOAuth}
						disabled={loading}
						class="w-full mt-2 bg-gradient-to-r from-orange-500 to-rose-600 text-white font-semibold text-sm py-2.5 rounded hover:from-orange-400 hover:to-rose-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
					>
						Connect to Strava
					</button>
				</div>
			</div>

		{:else if step === 'waiting'}
			<!-- Waiting for OAuth -->
			<div class="bg-slate-900/50 border border-slate-800 rounded-lg p-6 text-center">
				<div class="inline-block mb-4">
					<svg class="w-8 h-8 text-orange-500 animate-spin" viewBox="0 0 24 24" fill="none">
						<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.25"/>
						<path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
					</svg>
				</div>
				<h2 class="text-lg font-semibold text-slate-200 mb-2">Waiting for authorization...</h2>
				<p class="text-sm text-slate-400">A popup should have opened to Strava. Authorize the app there.</p>
				<p class="text-xs text-slate-600 mt-3">If the popup was blocked, <button class="text-sky-400 underline cursor-pointer" onclick={() => { step = 'credentials'; loading = false; }}>go back</button> and try again.</p>
			</div>

		{:else if step === 'success'}
			<!-- Connected -->
			<div class="bg-slate-900/50 border border-slate-800 rounded-lg p-6 text-center">
				<div class="inline-block mb-4">
					<svg class="w-10 h-10 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M20 6L9 17l-5-5"/>
					</svg>
				</div>
				<h2 class="text-lg font-semibold text-emerald-400 mb-2">Connected to Strava!</h2>
				<p class="text-sm text-slate-400">Loading your dashboard...</p>
			</div>
		{/if}

		<!-- Footer -->
		<p class="text-center text-[10px] text-slate-700 mt-6">Your credentials are stored locally and never leave this machine.</p>
	</div>
</div>
