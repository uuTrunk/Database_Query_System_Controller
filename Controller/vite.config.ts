import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'
import yaml from 'js-yaml'

// Parse config.yaml to get Agent and Training ports
let agentPort = '8000';
let trainingPort = '8001';
let authUser = 'admin';
let authPass = '';

try {
  const configPath = path.resolve(__dirname, '../config/config.yaml');
  if (fs.existsSync(configPath)) {
    const fileContents = fs.readFileSync(configPath, 'utf8');
    const data = yaml.load(fileContents) as any;
    if (data.agent_port) agentPort = data.agent_port.toString();
    if (data.training_port) trainingPort = data.training_port.toString();
    if (data.auth) {
      if (data.auth.username) authUser = data.auth.username.toString();
      if (data.auth.password) authPass = data.auth.password.toString();
    }
  }
} catch (e) {
  console.error('Failed to read config.yaml', e);
}

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom'
  },
  define: {
    __AGENT_PORT__: JSON.stringify(agentPort),
    __TRAINING_PORT__: JSON.stringify(trainingPort),
    __AUTH_USER__: JSON.stringify(authUser),
    __AUTH_PASS__: JSON.stringify(authPass)
  }
})
