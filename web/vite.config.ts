import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/ws': {
				target: 'http://127.0.0.1:8000',
				ws: true
			},
			'/api': {
				target: 'http://127.0.0.1:8000'
			},
			'/auth': {
				target: 'http://127.0.0.1:8000'
			}
		}
	}
});
