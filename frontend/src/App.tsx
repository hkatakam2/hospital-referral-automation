import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { ReferralInboxPage } from './pages/ReferralInboxPage'
import { ReferralDetailPage } from './pages/ReferralDetailPage'

export default function App() {
  return <BrowserRouter>
    <main>
      <header><Link className="brand" to="/referrals"><span className="mark" aria-hidden="true">+</span> Referral workspace</Link><span className="badge">Synthetic data prototype</span></header>
      <Routes>
        <Route path="/" element={<Navigate to="/referrals" replace />} />
        <Route path="/referrals" element={<ReferralInboxPage />} />
        <Route path="/referrals/:referralId" element={<ReferralDetailPage />} />
        <Route path="*" element={<p>Page not found. <Link to="/referrals">Return to inbox</Link></p>} />
      </Routes>
      <footer>Hospital Referral Automation · Administrative review prototype</footer>
    </main>
  </BrowserRouter>
}
