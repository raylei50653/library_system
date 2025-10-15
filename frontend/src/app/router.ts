import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { setupAuthGuard } from './guards/auth-guard'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('@/features/home/pages/HomeView.vue'), meta: { title: '首頁' } },

  // ======= 訪客區 =======
  { path: '/login', name: 'login', component: () => import('@/features/auth/pages/LoginView.vue'), meta: { guest: true, layout: 'blank', title: '登入' } },
  { path: '/register', name: 'register', component: () => import('@/features/auth/pages/RegisterView.vue'), meta: { guest: true, layout: 'blank', title: '註冊' } },

  // ======= 使用者區 =======
  { path: '/books', name: 'books', component: () => import('@/features/books/pages/BooksListView.vue'), meta: { title: '館藏' } },
  { path: '/loans', name: 'loans', component: () => import('@/features/loans/pages/LoansListView.vue'), meta: { requiresAuth: true, title: '借閱紀錄' } },
  { path: '/favorites', name: 'favorites', component: () => import('@/features/favorites/pages/FavoritesView.vue'), meta: { requiresAuth: true, title: '收藏' } },
  { path: '/profile', name: 'profile', component: () => import('@/features/profile/pages/ProfileView.vue'), meta: { requiresAuth: true, title: '個人資料' } },
  { path: '/notifications', component: () => import('@/features/notifications/pages/NotificationsView.vue'), meta: { requiresAuth: true } },
  { path: '/chat', name: 'chat-home', component: () => import('@/features/chat/pages/ChatCenterView.vue'), meta: { requiresAuth: true, title: '客服中心' } },
  { path: '/chat/tickets/:id', name: 'ticket', props: true, component: () => import('@/features/chat/pages/TicketDetailView.vue'), meta: { requiresAuth: true, title: '票單' } },

  // ======= 404 =======
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL), // 若沒設 base，可改回 createWebHistory()
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

setupAuthGuard(router)

// 可選：動態設定頁標題
router.afterEach((to) => {
  const title = (to.meta?.title as string) ?? 'Library System'
  document.title = title
})

export default router
