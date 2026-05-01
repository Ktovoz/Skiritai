import { createBrowserRouter } from 'react-router-dom'
import App from '../App'
import CaseList from '../pages/CaseList'
import CaseDetail from '../pages/CaseDetail'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <CaseList /> },
      { path: 'case/:caseId', element: <CaseDetail /> },
    ],
  },
])

export default router
