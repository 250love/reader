<template>
  <div class="app-shell" :class="{ 'auth-shell': route.name === 'auth' }">
    <header v-if="showTopNav" class="top-nav">
      <div>
        <p class="brand-kicker">Paper Reader Lab</p>
        <h1>论文阅读管理器</h1>
      </div>

      <div class="top-nav-actions">
        <nav>
          <RouterLink :to="{ name: 'dashboard' }">论文管理</RouterLink>
          <RouterLink :to="{ name: 'citations' }">引用助手</RouterLink>
          <RouterLink :to="{ name: 'academic-ai' }">学术 AI</RouterLink>
        </nav>

        <div class="user-entry-wrap" ref="menuRootRef">
          <button class="user-entry-btn" @click="toggleMenu">
            {{ userInitial }}
          </button>

          <section v-if="menuOpen" class="user-entry-menu">
            <div class="menu-user-head">
              <p class="menu-user-mask">{{ maskedAccount }}</p>
              <span class="menu-user-tier">BASIC 基础版</span>
              <p class="menu-meta">账号中心</p>
            </div>

            <div class="menu-divider" />

            <button class="menu-action" @click="goSettings">账号设置</button>
            <button class="menu-action danger" @click="onLogout">退出登录</button>
          </section>
        </div>
      </div>
    </header>

    <main>
      <RouterView v-slot="{ Component }">
        <KeepAlive include="AcademicAIView">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { clearAuth, getUser, isAuthed } from "@/services/auth";

const route = useRoute();
const router = useRouter();
const menuOpen = ref(false);
const menuRootRef = ref(null);

const currentUser = computed(() => getUser() || {});
const showTopNav = computed(() => route.name !== "auth" && isAuthed());

const userInitial = computed(() => {
  const source =
    currentUser.value?.display_name || currentUser.value?.username || currentUser.value?.email || "U";
  return source.slice(0, 1).toUpperCase();
});

const maskedAccount = computed(() => {
  const raw = currentUser.value?.email || currentUser.value?.username || "未登录用户";
  if (raw.includes("@")) {
    const [name, domain] = raw.split("@");
    const safeName = name.length <= 2 ? `${name[0] || "*"}*` : `${name.slice(0, 2)}***${name.slice(-1)}`;
    return `${safeName}@${domain}`;
  }

  if (raw.length >= 7) {
    return `${raw.slice(0, 3)}****${raw.slice(-2)}`;
  }
  if (raw.length >= 3) {
    return `${raw[0]}***${raw.slice(-1)}`;
  }
  return raw;
});

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

function closeMenu() {
  menuOpen.value = false;
}

function handleDocumentClick(event) {
  if (!menuOpen.value) return;
  const root = menuRootRef.value;
  if (!root) return;
  if (!root.contains(event.target)) {
    closeMenu();
  }
}

function goSettings() {
  closeMenu();
  router.push({ name: "settings" });
}

function onLogout() {
  closeMenu();
  clearAuth();
  router.push({ name: "auth" });
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
});
</script>

<style scoped>
.auth-shell {
  width: 100%;
  margin: 0;
}

.top-nav-actions {
  display: flex;
  align-items: center;
  gap: 0.72rem;
}

.user-entry-wrap {
  position: relative;
}

.user-entry-btn {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid #cfdde6;
  background: radial-gradient(circle at 35% 30%, #f8fdff 0%, #e7eff5 100%);
  color: #3c5568;
  font-weight: 700;
  font-size: 1.05rem;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(40, 63, 78, 0.14);
}

.user-entry-menu {
  position: absolute;
  top: calc(100% + 0.6rem);
  right: 0;
  width: min(286px, 90vw);
  background: linear-gradient(180deg, #ffffff 0%, #f9fcff 100%);
  border: 1px solid #d7dee7;
  border-radius: 16px;
  box-shadow: 0 18px 42px rgba(17, 32, 48, 0.18);
  padding: 0.82rem;
  z-index: 100;
}

.user-entry-menu::before {
  content: "";
  position: absolute;
  right: 14px;
  top: -8px;
  width: 14px;
  height: 14px;
  background: #fff;
  border-top: 1px solid #d7dee7;
  border-left: 1px solid #d7dee7;
  transform: rotate(45deg);
}

.menu-user-head {
  display: grid;
  gap: 0.22rem;
}

.menu-user-mask {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1e2530;
  letter-spacing: 0.015em;
}

.menu-user-tier {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  border-radius: 7px;
  padding: 0.2rem 0.42rem;
  background: #d6f4e7;
  color: #0d7556;
  font-weight: 700;
  font-size: 0.72rem;
}

.menu-meta {
  margin: 0;
  font-size: 0.8rem;
  color: #5f7387;
}

.menu-divider {
  margin: 0.66rem 0 0.5rem;
  border-top: 1px solid #e2e6ec;
}

.menu-action {
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0.58rem 0.4rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #27394b;
  cursor: pointer;
}

.menu-action:hover {
  background: #eef4fa;
  color: #183f63;
}

.menu-action.danger {
  color: #8d2f2f;
}

.menu-action.danger:hover {
  background: #fff0f0;
  color: #7c2020;
}

@media (max-width: 980px) {
  .top-nav {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.55rem;
  }

  .top-nav-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

}
</style>
