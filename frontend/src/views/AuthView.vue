<template>
  <section class="auth-page" :style="{ '--auth-bg-image': `url(${authBackground})` }">
    <div class="auth-overlay" />
    <div class="auth-wrap">
      <div class="auth-hero">
        <p class="hero-kicker">Paper Reader</p>
        <h2>Read Better. Think Deeper.</h2>
      </div>

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

import authBackground from "@/assets/auth-background.jpg";
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
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem 1rem;
  overflow: hidden;
  background-image: var(--auth-bg-image);
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  isolation: isolate;
}

.auth-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background: inherit;
  transform: scale(1.02);
  z-index: -3;
}

.auth-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(7, 14, 24, 0.28), rgba(255, 255, 255, 0.08)),
    rgba(10, 18, 28, 0.22);
  z-index: -2;
}

.auth-wrap {
  width: min(960px, 94vw);
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(320px, 430px);
  align-items: center;
  gap: 1.25rem;
  z-index: 1;
}

.auth-hero {
  color: #fff;
  text-shadow: 0 3px 18px rgba(0, 0, 0, 0.42);
}

.hero-kicker {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.84);
  font-weight: 700;
}

.auth-hero h2 {
  margin: 0.4rem 0 0.6rem;
  font-size: clamp(2rem, 5vw, 4.4rem);
  line-height: 1.1;
  max-width: 8.4em;
}

.auth-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.62);
  border-radius: 22px;
  padding: 1.15rem;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 24px 60px rgba(24, 38, 52, 0.24);
}

.tab-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
}

.tab-row button {
  background: rgba(255, 255, 255, 0.64);
  border-color: rgba(171, 187, 199, 0.72);
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
  border: 1px solid rgba(187, 198, 207, 0.9);
  border-radius: 10px;
  padding: 0.62rem 0.72rem;
  font: inherit;
  color: #1d2a36;
  background: rgba(255, 255, 255, 0.88);
  outline: none;
}

.auth-form input:focus {
  border-color: #0f6d64;
  box-shadow: 0 0 0 3px rgba(15, 109, 100, 0.16);
}

.code-line,
.password-line {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem;
}

.strength-panel {
  border: 1px solid rgba(216, 224, 230, 0.86);
  background: rgba(246, 250, 252, 0.78);
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
  background: rgba(255, 255, 255, 0.86);
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

@media (max-width: 920px) {
  .auth-wrap {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .auth-hero {
    text-align: center;
  }

  .auth-hero h2 {
    max-width: 11em;
    font-size: clamp(1.8rem, 10vw, 3rem);
  }

  .code-line,
  .password-line {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .auth-page {
    padding: 1.2rem 0.85rem;
  }

  .auth-card {
    border-radius: 18px;
    padding: 0.9rem;
  }
}
</style>
