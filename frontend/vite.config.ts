import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { voicePlugin } from './server/voice-plugin.mjs';
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxy = { '/api': {
    target: env.CARECOMPASS_API_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api(?=\/|$)/, ''),
  } };
  return {
    plugins: [voicePlugin(env), react()],
    resolve: { preserveSymlinks: true },
    server: { port: 5173, strictPort: true, proxy },
    preview: { proxy },
  };
});
