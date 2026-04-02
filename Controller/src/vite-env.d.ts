/// <reference types="vite/client" />
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare const __AGENT_PORT__: string
declare const __TRAINING_PORT__: string
declare const __AUTH_USER__: string
declare const __AUTH_PASS__: string
