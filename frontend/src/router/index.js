import { createRouter, createWebHistory } from "vue-router";

import AuthView from "@/views/AuthView.vue";
import AcademicAIView from "@/views/AcademicAIView.vue";
import CitationAssistantView from "@/views/CitationAssistantView.vue";
import DashboardView from "@/views/DashboardView.vue";
import ReaderView from "@/views/ReaderView.vue";
import SettingsView from "@/views/SettingsView.vue";
import { isAuthed } from "@/services/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/auth", name: "auth", component: AuthView, meta: { guestOnly: true } },
    {
      path: "/",
      redirect: () => (isAuthed() ? "/dashboard" : "/auth")
    },
    { path: "/dashboard", name: "dashboard", component: DashboardView, meta: { requiresAuth: true } },
    {
      path: "/citations",
      name: "citations",
      component: CitationAssistantView,
      meta: { requiresAuth: true }
    },
    {
      path: "/academic-ai",
      name: "academic-ai",
      component: AcademicAIView,
      meta: { requiresAuth: true }
    },
    {
      path: "/reader/:id",
      name: "reader",
      component: ReaderView,
      props: true,
      meta: { requiresAuth: true }
    },
    { path: "/settings", name: "settings", component: SettingsView, meta: { requiresAuth: true } }
  ]
});

router.beforeEach((to) => {
  const authed = isAuthed();
  if (to.meta.guestOnly && authed) {
    return { name: "dashboard" };
  }
  if (to.meta.requiresAuth && !authed) {
    return { name: "auth" };
  }
  return true;
});

export default router;
