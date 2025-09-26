import * as React from "react";
import { useEffect } from "react";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Plus, Mic } from "lucide-react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router";
import { useAuth } from "hooks/useAuth";
import { usePodcasts } from "hooks/usePodcast";
import StatsOverview from "~/components/dashboard/StatsOverview";
import PodcastCard from "~/components/dashboard/PodcastCard";
import TranslationStatus from "~/components/dashboard/TranslationStatus";
import EmptyState from "~/components/dashboard/EmptyState";

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { 
    podcasts, 
    translations, 
    isLoading, 
    error, 
    refreshData 
  } = usePodcasts();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/auth/login");
      return;
    }

    if (user && !user.onboarding_completed && podcasts.length === 0) {
      navigate("/onboarding/rss-feed");
      return;
    }

    // Load data when component mounts
    if (isAuthenticated && user?.onboarding_completed) {
      refreshData();
    }
  }, [isAuthenticated, user, authLoading, navigate, refreshData, podcasts.length]);

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-full"></div>
          <div className="text-xl font-medium text-gray-600">Loading your podcasts...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl font-medium text-red-600 mb-4">Error loading dashboard</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <Button onClick={refreshData}>Try Again</Button>
        </div>
      </div>
    );
  }

  const stats = {
    totalPodcasts: podcasts.length,
    totalLanguages: [...new Set(translations.map(t => t.target_language))].length,
    totalTranslations: translations.length,
    activeTranslations: translations.filter(t => t.status === 'published').length
  };

  return (
    <div className="min-h-screen p-6 md:p-8 bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4"
        >
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
              Welcome back, {user?.full_name?.split(' ')[0] || 'there'}! 👋
            </h1>
            <p className="text-gray-600">
              {podcasts.length === 0
                ? "Ready to globalize your first podcast?"
                : `You have ${stats.totalTranslations} translations across ${stats.totalLanguages} languages`
              }
            </p>
          </div>
          <Link to="/onboarding/rss-feed">
            <Button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium px-6 py-3 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]">
              <Plus className="w-5 h-5 mr-2" />
              Add New Podcast
            </Button>
          </Link>
        </motion.div>

        <StatsOverview stats={stats} />

        {podcasts.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <Card className="backdrop-blur-md bg-white/80 shadow-lg border-0">
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Mic className="w-5 h-5 text-blue-600" />
                        My Podcasts
                      </span>
                      <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                        {podcasts.length}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {podcasts.map((podcast, index) => (
                      <PodcastCard
                        key={podcast.id}
                        podcast={podcast}
                        translations={translations.filter(t => t.podcast_id === podcast.id)}
                        index={index}
                      />
                    ))}
                  </CardContent>
                </Card>
              </motion.div>
            </div>
            <div>
              <TranslationStatus translations={translations} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}