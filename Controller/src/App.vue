<template>
  <div id="app">
    <!-- Login Screen -->
    <div v-if="!isLoggedIn" class="card">
      <h1>Data Copilot</h1>
      <p style="color: #888; font-size: 1.1em; margin-bottom: 2rem;">
        Intelligent Database Query Generation
      </p>
      
      <div style="display: flex; flex-direction: column; align-items: center; gap: 15px;">
        <input 
          v-model="username" 
          type="text" 
          placeholder="Account ID"
          style="width: 250px;" 
        />
        <input 
          v-model="password" 
          type="password" 
          placeholder="Password" 
          @keyup.enter="login" 
          style="width: 250px;" 
        />
        <p v-if="loginError" style="color: #ff5555; text-shadow: 0 0 5px rgba(255,0,0,0.5);">Authentication Failed, Please Check Backend Logs.</p>
        <button @click="login" style="width: 275px; margin-top: 10px; background: rgba(66, 211, 146, 0.1); border: 1px solid #42d392; color: #42d392;">
          Enter System Space
        </button>
      </div>
    </div>

    <!-- Dashboard Screen -->
    <div v-else>
      <h1>Copilot Workstation</h1>
      <p style="color: #42d392; font-weight: 500;">Connection Secure: Connected to Ports {{ agentPort }} & {{ trainingPort }}. </p>
      
      <div class="card" style="display: flex; gap: 10px; justify-content: center; align-items: center;">
        <input 
          v-model="question" 
          type="text" 
          placeholder="Ask a question about the database..." 
          @keyup.enter="askQuestion" 
          style="width: 60%; background: #111; font-size: 1.1em; padding: 12px 20px;" 
        />
        <button 
          @click="askQuestion" 
          :disabled="isProcessing"
          style="font-size: 1.1em; padding: 12px 24px; background: rgba(100, 108, 255, 0.1); color: #646cff; border: 1px solid #646cff;"
        >
          Generate ✨
        </button>
      </div>
      
      <!-- Processing Info -->
      <div v-if="isProcessing" style="margin: 20px 0; color: #888; animation: pulse 1.5s infinite;">
        <p style="font-size: 1.2em; color: #fff;">{{ currentQuestion }}</p>
        <p>Inferring optimal concurrency thread count via ML Node...</p>
        <p v-if="predictionData" style="color: #42d392;">
          Neural Evaluation Score: {{ predictionData.score.toFixed(4) }} | Spawning <strong>[ {{ predictionData.threads }} ]</strong> Generation Nodes.
        </p>
        <p style="font-style: italic;">Wait... Chart Rendering from Concurrent Pipelines</p>
      </div>

      <!-- Results Grid -->
      <div v-if="!isProcessing && results.length > 0" class="results-grid" style="margin-top: 30px; display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;">
        <div v-for="(res, index) in results" :key="index" style="background: #1f1f1f; border-radius: 12px; padding: 20px; border: 1px solid #333; max-width: 600px; width: 100%;">
          <template v-if="res.success">
            <h3 style="color: #42d392; margin-top: 0; display: flex; align-items: center; gap: 10px;">
              <span style="background: rgba(66,211,146,0.2); padding: 5px 10px; border-radius: 6px; font-size: 0.8em;">Thread {{ index + 1 }}</span>
              Generation Success
            </h3>
            <img :src="'data:image/png;base64,' + res.image" style="width: 100%; border-radius: 8px; border: 1px solid #444;" />
          </template>
          <template v-else>
            <h3 style="color: #ff5555; margin-top: 0; display: flex; align-items: center; gap: 10px;">
               <span style="background: rgba(255,85,85,0.2); padding: 5px 10px; border-radius: 6px; font-size: 0.8em;">Thread {{ index + 1 }}</span>
               Failed
            </h3>
            <p style="color: #aaa; text-align: left; padding: 10px; background: #111; border-radius: 6px; font-family: monospace;">
              {{ res.error }}
            </p>
          </template>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

// Constants imported from Vite Define mappings
/* global __AGENT_PORT__, __TRAINING_PORT__, __AUTH_USER__, __AUTH_PASS__ */
const agentPort = __AGENT_PORT__;
const trainingPort = __TRAINING_PORT__;

const AGENT_API = `http://localhost:${agentPort}/api`;
const TRAINING_API = `http://localhost:${trainingPort}/api`;

const isLoggedIn = ref(false);
const username = ref(__AUTH_USER__);
const password = ref(__AUTH_PASS__);
const loginError = ref(false);

const question = ref('');
const currentQuestion = ref('');
const isProcessing = ref(false);
const predictionData = ref(null);
const results = ref([]);

onMounted(() => {
  // component mounted
});

async function login() {
  loginError.value = false;
  try {
    const res = await fetch(`${AGENT_API}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value })
    });
    
    if (res.ok) {
      isLoggedIn.value = true;
    } else {
      loginError.value = true;
    }
  } catch (err) {
    console.error(err);
    loginError.value = true;
  }
}

async function askQuestion() {
  if (!question.value.trim() || isProcessing.value) return;
  currentQuestion.value = question.value;
  isProcessing.value = true;
  predictionData.value = null;
  results.value = [];

  try {
    const pReq = await fetch(`${TRAINING_API}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: currentQuestion.value })
    });
    const pData = await pReq.json();
    predictionData.value = { score: pData.score || 0.2, threads: pData.threads || 1 };
    
    const reqBody = {
      question: currentQuestion.value,
      concurrent: [1, 1],
      retries: [5, 5]
    };
    
    const fetchPromises = [];
    for (let i = 0; i < predictionData.value.threads; i++) {
      fetchPromises.push(
        fetch(`${AGENT_API}/ask/graph-steps`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(reqBody)
        }).then(r => r.json()).catch(e => ({ msg: e.toString() }))
      );
    }
    
    const responses = await Promise.all(fetchPromises);
    
    responses.forEach(data => {
      if (data.code === 200 && data.image_data) {
        results.value.push({ success: true, image: data.image_data });
      } else {
        results.value.push({ success: false, error: data.msg || 'unknown error' });
      }
    });

  } catch (err) {
    console.error(err);
    alert('An error occurred: ' + err);
  } finally {
    isProcessing.value = false;
    question.value = '';
  }
}
</script>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42d883aa);
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}
</style>
