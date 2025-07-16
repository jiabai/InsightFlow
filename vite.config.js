import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: './src/background/index.js',
        content: './src/content/index.js'
      },
      output: {
        entryFileNames: `[name].js`,
      }
    },
    minify: false
  }
});