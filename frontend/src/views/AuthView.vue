<template>
  <section class="auth-page">
    <div class="aurora aurora-a" />
    <div class="aurora aurora-b" />
    <div class="auth-wrap">
      <aside class="auth-hero">
        <p class="hero-kicker">Paper Reader</p>
        <h2>Read Better. Think Deeper.</h2>
        <p>Sign in to manage papers, read in dual-pane mode, and configure translation providers.</p>
      </aside>

      <section class="auth-card">
        <div class="tab-row">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Login</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Register</button>
        </div>

        <form v-if="mode === 'login'" class="auth-form" @submit.prevent="onLogin">
          <input v-model="loginForm.identifier" placeholder="Email or username" type="text" required />
          <input
            v-model="loginForm.password"
            placeholder="Password"
            type="password"
            required
          />
          <button :disabled="loading">{{ loading ? "Signing in..." : "Sign in" }}</button>
        </form>

        <form v-else class="auth-form" @submit.prevent="onRegister">
          <input v-model="registerForm.email" placeholder="Email" type="email" required />
          <div class="code-line">
            <input v-model="registerForm.code" placeholder="6-digit code" maxlength="6" required />
            <button
              type="button"
              class="outline"
              @click="onSendCode"
              :disabled="codeSending || countdown > 0"
            >
              {{ countdown > 0 ? `${countdown}s` : codeSending ? "Sending..." : "Send code" }}
            </button>
          </div>

          <input v-model="registerForm.display_name" placeholder="Display name (optional)" />

          <div class="password-line">
            <input
              v-model="registerForm.password"
              placeholder="Password (min 8 chars)"
              type="password"
              minlength="8"
              required
            />
            <button
              type="button"
              class="outline"
              @click="onRecommendPassword"
              :disabled="loading || passwordSuggesting"
            >
              {{ passwordSuggesting ? "Generating..." : "Generate" }}
            </button>
          </div>

          <div class="strength-panel">
            <div class="strength-title">
              <span>Password Strength</span>
              <span :class="`level-${passwordStrength.level}`">{{ passwordStrength.label }}</span>
            </div>
            <div class="strength-bars">
              <span
                v-for="i in 6"
                :key="i"
                :class="[
                  'strength-bar',
                  i <= passwordStrength.score ? `fill-${passwordStrength.level}` : ''
                ]"
              />
            </div>
            <p class="strength-hint">
              Use uppercase, lowercase, numbers and symbols for better security.
            </p>
          </div>

          <input
            v-model="registerForm.confirm_password"
            placeholder="Confirm password"
            type="password"
            minlength="8"
            required
          />
          <p v-if="passwordMatchError" class="error inline-error">{{ passwordMatchError }}</p>

          <button :disabled="loading || !!passwordMatchError">
            {{ loading ? "Registering..." : "Register and sign in" }}
          </button>
        </form>

        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";

import { login, recommendPassword, register, sendRegisterCode } from "@/services/api";
import { setAuth } from "@/services/auth";

const router = useRouter();

const mode = ref("login");
const loading = ref(false);
const codeSending = ref(false);
const passwordSuggesting = ref(false);
const countdown = ref(0);
const timer = ref(null);
const message = ref("");
const errorMsg = ref("");

const loginForm = ref({
  identifier: "",
  password: ""
});

const registerForm = ref({
  email: "",
  code: "",
  display_name: "",
  password: "",
  confirm_password: ""
});

const passwordStrength = computed(() => evaluatePassword(registerForm.value.password));

const passwordMatchError = computed(() => {
  if (!registerForm.value.confirm_password) return "";
  return registerForm.value.password === registerForm.value.confirm_password
    ? ""
    : "Passwords do not match.";
});

function evaluatePassword(password) {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  let label = "Weak";
  let level = "weak";
  if (score >= 5) {
    label = "Strong";
    level = "strong";
  } else if (score >= 3) {
    label = "Medium";
    level = "medium";
  }

  return { score, label, level };
}

function setError(error) {
  errorMsg.value = error?.response?.data?.error || error?.message || "Request failed. Please try again.";
}

async function onSendCode() {
  if (!registerForm.value.email.trim()) {
    errorMsg.value = "Please fill in your email first.";
    return;
  }
  codeSending.value = true;
  errorMsg.value = "";
  message.value = "";
  try {
    const result = await sendRegisterCode({
      email: registerForm.value.email.trim(),
      purpose: "register"
    });
    message.value = result.debug_code
      ? `Code sent (dev mode): ${result.debug_code}`
      : "Code sent. Please check your inbox.";
    startCountdown();
  } catch (error) {
    setError(error);
  } finally {
    codeSending.value = false;
  }
}

async function onRecommendPassword() {
  passwordSuggesting.value = true;
  errorMsg.value = "";
  message.value = "";
  try {
    const result = await recommendPassword({
      email: registerForm.value.email.trim(),
      display_name: registerForm.value.display_name.trim()
    });
    registerForm.value.password = result.recommended_password;
    registerForm.value.confirm_password = result.recommended_password;
    message.value = `Recommended password generated (${result.strength.label}). Save it safely.`;
  } catch (error) {
    setError(error);
  } finally {
    passwordSuggesting.value = false;
  }
}

function startCountdown() {
  countdown.value = 60;
  if (timer.value) clearInterval(timer.value);
  timer.value = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      clearInterval(timer.value);
      timer.value = null;
    }
  }, 1000);
}

async function onLogin() {
  loading.value = true;
  errorMsg.value = "";
  message.value = "";
  try {
    const result = await login({
      identifier: loginForm.value.identifier.trim(),
      password: loginForm.value.password
    });
    setAuth(result.token, result.user);
    router.push({ name: "dashboard" });
  } catch (error) {
    setError(error);
  } finally {
    loading.value = false;
  }
}

async function onRegister() {
  if (passwordMatchError.value) {
    errorMsg.value = passwordMatchError.value;
    return;
  }

  loading.value = true;
  errorMsg.value = "";
  message.value = "";
  try {
    const result = await register({
      email: registerForm.value.email.trim(),
      password: registerForm.value.password,
      confirm_password: registerForm.value.confirm_password,
      code: registerForm.value.code.trim(),
      display_name: registerForm.value.display_name.trim()
    });
    setAuth(result.token, result.user);
    router.push({ name: "dashboard" });
  } catch (error) {
    setError(error);
  } finally {
    loading.value = false;
  }
}

onBeforeUnmount(() => {
  if (timer.value) clearInterval(timer.value);
});
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 86vh;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.aurora {
  position: absolute;
  border-radius: 999px;
  filter: blur(18px);
  opacity: 0.42;
  animation: drift 8s ease-in-out infinite;
}

.aurora-a {
  width: 300px;
  height: 300px;
  background: #a8ece2;
  left: -60px;
  top: 60px;
}

.aurora-b {
  width: 360px;
  height: 360px;
  background: #ffd8ba;
  right: -100px;
  bottom: -80px;
  animation-delay: 1.2s;
}

.auth-wrap {
  width: min(920px, 94vw);
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 1rem;
  z-index: 2;
}

.auth-hero {
  padding: 1.4rem 1.2rem;
}

.hero-kicker {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #466070;
}

.auth-hero h2 {
  margin: 0.4rem 0 0.6rem;
  font-size: clamp(1.5rem, 2.6vw, 2.5rem);
  line-height: 1.1;
}

.auth-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(196, 210, 220, 0.95);
  border-radius: 18px;
  padding: 1rem;
  backdrop-filter: blur(12px);
  box-shadow: 0 12px 32px rgba(34, 54, 72, 0.12);
}

.tab-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
}

.tab-row button {
  background: #edf3f6;
  border-color: #c9d7de;
  color: #22384a;
}

.tab-row button.active {
  background: #0f6d64;
  color: #fff;
  border-color: #0f6d64;
}

.auth-form {
  display: grid;
  gap: 0.6rem;
}

.auth-form input {
  border: 1px solid #d5dbe2;
  border-radius: 10px;
  padding: 0.62rem 0.72rem;
  font: inherit;
}

.code-line,
.password-line {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem;
}

.strength-panel {
  border: 1px solid #d8e0e6;
  background: #f6fafc;
  border-radius: 12px;
  padding: 0.6rem 0.7rem;
}

.strength-title {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 0.42rem;
}

.strength-bars {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0.36rem;
}

.strength-bar {
  height: 7px;
  border-radius: 999px;
  background: #d9e2e8;
}

.fill-weak {
  background: linear-gradient(90deg, #f08e8e, #e95a5a);
}

.fill-medium {
  background: linear-gradient(90deg, #f4c26f, #f0a42e);
}

.fill-strong {
  background: linear-gradient(90deg, #34c38f, #10a56f);
}

.level-weak {
  color: #c94a43;
}

.level-medium {
  color: #b47b20;
}

.level-strong {
  color: #167c5a;
}

.strength-hint {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: #5a6e80;
}

.outline {
  background: #fff;
  color: #1f3a4d;
  border-color: #cad7de;
}

.error {
  color: #b7382b;
  margin: 0.8rem 0 0;
}

.inline-error {
  margin: -0.1rem 0 0.1rem;
}

.message {
  color: #11534f;
  margin: 0.8rem 0 0;
}

@keyframes drift {
  0% {
    transform: translateY(0) translateX(0);
  }
  50% {
    transform: translateY(14px) translateX(-8px);
  }
  100% {
    transform: translateY(0) translateX(0);
  }
}

@media (max-width: 920px) {
  .auth-wrap {
    grid-template-columns: 1fr;
  }

  .code-line,
  .password-line {
    grid-template-columns: 1fr;
  }
}
</style>
