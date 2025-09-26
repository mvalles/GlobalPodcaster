import React, { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { 
  Globe, 
  Settings, 
  HelpCircle, 
  LogOut, 
  User as UserIcon
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "~/components/ui/avatar";
import { useAuth } from "hooks/useAuth";

const Navbar = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const [currentPageName, setCurrentPageName] = React.useState("");
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // Determinar página actual
    const pathname = location.pathname;
    if (pathname === "/dashboard") {
      setCurrentPageName("Dashboard");
    } else if (pathname === "/monitoring") {
      setCurrentPageName("Monitoring");
    } else if (pathname === "/settings") {
      setCurrentPageName("Settings");
    } else {
      setCurrentPageName("");
    }
  }, [location.pathname]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/auth/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <nav className="backdrop-blur-md bg-white/80 border-b border-white/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <Globe className="w-6 h-6 text-white" />
            </div>
            <div className="font-bold text-xl bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              Global Podcaster
            </div>
          </Link>

          <div className="flex items-center gap-6">
            {!isAuthenticated ? (
              <>
                <Link to="/auth/login" className="font-medium text-gray-600 hover:text-gray-900 transition-colors">Login</Link>
                <Link to="/auth/signup" className="font-medium text-gray-600 hover:text-gray-900 transition-colors">Signup</Link>
              </>
            ) : (
              <>
                <Link 
                  to="/dashboard"
                  className={`font-medium transition-colors ${
                    currentPageName === 'Dashboard' 
                      ? 'text-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Dashboard
                </Link>
                <Link 
                  to="/monitoring"
                  className={`font-medium transition-colors ${
                    currentPageName === 'Monitoring' 
                      ? 'text-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Monitoring
                </Link>
                <Link 
                  to="/settings"
                  className={`font-medium transition-colors ${
                    currentPageName === 'Settings' 
                      ? 'text-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Settings
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger className="focus:outline-none">
                    <Avatar className="w-9 h-9 ring-2 ring-blue-500/20 hover:ring-blue-500/40 transition-all">
                      <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white font-semibold">
                        {user?.full_name?.[0]?.toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56 bg-white/95 backdrop-blur-md">
                    <div className="px-3 py-2">
                      <p className="font-medium text-gray-900">{user?.full_name || "User"}</p>
                      <p className="text-sm text-gray-500">{user?.email || "user@example.com"}</p>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/profile" className="flex items-center cursor-pointer">
                        <UserIcon className="w-4 h-4 mr-2" />
                        Profile
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/settings" className="flex items-center cursor-pointer">
                        <Settings className="w-4 h-4 mr-2" />
                        Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/help" className="flex items-center cursor-pointer">
                        <HelpCircle className="w-4 h-4 mr-2" />
                        Help & Support
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout} className="text-red-600 cursor-pointer">
                      <LogOut className="w-4 h-4 mr-2" />
                      Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;