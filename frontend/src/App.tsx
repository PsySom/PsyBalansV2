import { Box } from '@chakra-ui/react'
import { BrowserRouter as Router, Routes, Route, createBrowserRouter, RouterProvider } from 'react-router-dom'
import { routerFutureConfig } from './router-config'
import { Header } from './components'
import {
  Home,
  About,
  Onboarding,
  Dashboard,
  Calendar,
  Diaries,
  State,
  Recommendations,
  Profile,
  ScienceBase,
  NotificationCenter,
  NotFound
} from './pages'

// Создаем router с будущими флагами для предотвращения предупреждений
const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <Box as="main" minH="100vh">
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/diaries" element={<Diaries />} />
          <Route path="/state" element={<State />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/notifications" element={<NotificationCenter />} />
          <Route path="/science" element={<ScienceBase />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Box>
    )
  }
], routerFutureConfig);

// Совместимость с существующим кодом
function App() {
  // Используем старый Router для совместимости
  return (
    <Router future={routerFutureConfig}>
      <Box as="main" minH="100vh">
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/diaries" element={<Diaries />} />
          <Route path="/state" element={<State />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/notifications" element={<NotificationCenter />} />
          <Route path="/science" element={<ScienceBase />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Box>
    </Router>
  )
}

export default App