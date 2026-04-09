import { useNavigate, useLocation } from 'react-router-dom';
export { useParams } from 'react-router-dom';

export function useRouter() {
  const navigate = useNavigate();
  return {
    push: (path) => navigate(path),
    replace: (path) => navigate(path, { replace: true }),
    back: () => navigate(-1),
    forward: () => navigate(1),
    refresh: () => {},
  };
}

export function usePathname() {
  const location = useLocation();
  return location.pathname;
}

export function useSearchParams() {
  const location = useLocation();
  return new URLSearchParams(location.search);
}
