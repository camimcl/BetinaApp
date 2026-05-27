import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // ── Configuração do Vitest (testes de componente) ──────────────────────
  test: {
    // Simula um DOM real no Node.js para poder renderizar componentes React
    environment: "jsdom",

    // Executa o setup antes de cada arquivo de teste
    setupFiles: ["./src/__tests__/setup.js"],

    // Suporte a JSX global nos testes (sem precisar importar React em cada arquivo)
    globals: true,

    // Padrão de arquivos de teste reconhecidos
    include: ["src/__tests__/**/*.test.{js,jsx}"],

    // Exclui node_modules
    exclude: ["node_modules/**"],
  },
})
