import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { motion } from "framer-motion";
import {
  Globe,
  ArrowRight,
  ArrowLeft,
  Rss,
  CheckCircle,
  AlertCircle,
  Loader2,
  HelpCircle
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "~/components/ui/tooltip";
import { useApp } from "contexts/appContext";
import * as api from "services/api";

export default function OnboardingRSSFeed() {
  const navigate = useNavigate();
  const { createPodcast, state, dispatch, fetchPodcasts, fetchTranslations } = useApp();
  const [userChecked, setUserChecked] = useState(false);
  const [rssUrl, setRssUrl] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState(false);
  const [error, setError] = useState("");
  const [podcastData, setPodcastData] = useState<{ title?: string; description?: string; rss_feed_url?: string } | null>(null);
  const [hasFeed, setHasFeed] = useState(false);
  const [feedChecked, setFeedChecked] = useState(false);

  // Sin logs: verificación inicial de estado de usuario solo una vez
  useEffect(() => {
    if (!state.auth.user?.uid || userChecked) return;
    const checkOnboardingStatus = async () => {
      try {
        const currentUser = state.auth.user; // snapshot
        if (!currentUser) return;
        const userDoc = await api.fetchUser(currentUser.uid);
        if (userDoc && typeof userDoc.onboarding_completed !== "undefined") {
          // Solo despachar si cambia algo relevante para evitar renders en bucle
            if (
              userDoc.onboarding_completed !== currentUser.onboarding_completed ||
              userDoc.voice_sample_url !== currentUser.voice_sample_url ||
              userDoc.voice_prompt_seen !== currentUser.voice_prompt_seen
            ) {
              dispatch({ type: "UPDATE_USER", payload: { ...currentUser, ...userDoc } });
            }
            if (userDoc.onboarding_completed) {
              if (!userDoc.voice_sample_url && !userDoc.voice_prompt_seen) {
                navigate("/onboarding/voice-sample", { replace: true });
              } else {
                navigate("/dashboard", { replace: true });
              }
            }
        }
        setUserChecked(true);
      } catch {
        setUserChecked(true); // evitar reintentos infinitos en error
      }
    };
    checkOnboardingStatus();
  }, [state.auth.user?.uid, userChecked, dispatch, navigate]);

  // Efecto de feeds: dependencias reducidas para evitar re-render en cascada
  useEffect(() => {
    if (!state.auth.user?.uid || feedChecked) return;
    let cancelled = false;
    const currentUser = state.auth.user; // snapshot estable
    const checkUserFeeds = async () => {
      if (!currentUser) return;
      if (currentUser.onboarding_completed) {
        setFeedChecked(true);
        return;
      }
      try {
        const result = await api.getUserFeeds(currentUser.uid);
        const hasAny = Boolean(result.feeds && result.feeds.length > 0);
        setHasFeed(hasAny);
        if (!cancelled && hasAny && !currentUser.onboarding_completed) {
          // Actualizar usuario solo si realmente cambia onboarding_completed
          dispatch({ type: "UPDATE_USER", payload: { ...currentUser, onboarding_completed: true } });
          setFeedChecked(true);
          const needsVoice = !currentUser.voice_sample_url && !currentUser.voice_prompt_seen;
          navigate(needsVoice ? "/onboarding/voice-sample" : "/dashboard");
        } else {
          setFeedChecked(true);
        }
      } catch {
        setHasFeed(false);
        setFeedChecked(true);
      }
    };
    checkUserFeeds();
    return () => { cancelled = true; };
  }, [state.auth.user?.uid, feedChecked, dispatch, navigate]);

  const validateRSSFeed = async (url: any) => {
    if (!url || !url.startsWith('http')) {
      setError("Please enter a valid URL starting with http:// or https://");
      setIsValid(false);
      return;
    }
    setIsValidating(true);
    setError("");
    try {
      const result = await api.validateRssFeed(url);
      if (result.is_valid) {
        setIsValid(true);
        setPodcastData({
          rss_feed_url: url,
          title: result.title || "Untitled Podcast",
          description: result.description || "",
        });
      } else {
        setIsValid(false);
        setError(result.error || "This doesn't appear to be a valid podcast RSS feed");
      }
    } catch (error) {
      setIsValid(false);
      setError("Unable to validate RSS feed. Please check the URL and try again.");
    }
    setIsValidating(false);
  };

  const handleContinue = async () => {
    if (!podcastData || typeof podcastData.rss_feed_url !== 'string') return;
    try {
      if (createPodcast) {
        await createPodcast({
          ...podcastData,
          rss_feed_url: podcastData.rss_feed_url as string
        });
      }
      if (state.auth.user?.uid) {
        const response = await api.updateUser({ uid: state.auth.user.uid, onboarding_completed: true });
        if (response && response.user) {
          dispatch({ type: 'UPDATE_USER', payload: response.user });
        }
      }
      if (typeof fetchPodcasts === 'function') await fetchPodcasts();
      if (typeof fetchTranslations === 'function') await fetchTranslations();
      navigate("/dashboard");
    } catch (error: any) {
      setError(error.message || "Error creating podcast. Please try again.");
    }
  };

  const handleUrlChange = (value: any) => {
    setRssUrl(value);
    setIsValid(false);
    setError("");
    setPodcastData(null);
  };

  const handleValidate = () => {
    validateRSSFeed(rssUrl);
  };

  // Si el usuario aún no está cargado, muestra loader
  if (!state.auth.user?.uid) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="ml-3 text-blue-700">Loading user...</span>
      </div>
    );
  }

  // Redirección tardía de seguridad si onboarding ya completado
  useEffect(() => {
    if (state.auth.user?.onboarding_completed) {
      navigate("/dashboard", { replace: true });
    }
  }, [state.auth.user?.onboarding_completed, navigate]);

  // Show loading or error while checking feeds
  if (hasFeed === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="ml-3 text-blue-700">Checking your podcast feeds...</span>
      </div>
    );
  }
  if (hasFeed) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="w-full max-w-lg"
        >
          <Card className="backdrop-blur-md bg-white/90 shadow-2xl border-0 overflow-hidden">
            <CardHeader className="flex flex-col items-center gap-2 pb-4">
              <CheckCircle className="w-12 h-12 text-green-500 mb-2" />
              <CardTitle className="text-2xl font-bold text-gray-900">Podcast Feed Already Added</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 px-8 pb-8 text-center">
              <p className="text-gray-700 text-lg">
                You already have a <span className="font-semibold text-blue-700">podcast RSS feed</span> registered.<br />
                You can manage your feed and view episodes in the <span className="font-semibold text-purple-700">dashboard</span>.
              </p>
              <Button size="lg" className="mt-2 w-full flex items-center justify-center gap-2" onClick={() => navigate("/dashboard")}> 
                <ArrowRight className="w-5 h-5" /> Go to Dashboard
              </Button>
              <div className="mt-4 flex items-center justify-center gap-2 text-gray-400 text-sm">
                <Rss className="w-4 h-4" />
                <span>Only one feed can be registered per user.</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-2xl"
      >
        <Card className="backdrop-blur-md bg-white/80 shadow-2xl border-0 overflow-hidden">
          <CardHeader className="text-center pb-6">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center mx-auto mb-4">
              <Rss className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-2xl md:text-3xl font-bold text-gray-900">
              Add Your Podcast RSS Feed
            </CardTitle>
            <p className="text-gray-600 mt-2">
              Enter your podcast's RSS feed URL to get started with global distribution
            </p>
          </CardHeader>
          <CardContent className="space-y-6 px-8 pb-8">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Label htmlFor="rss_url" className="text-sm font-medium text-gray-700">
                  RSS Feed URL
                </Label>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">
                        You can find your RSS feed URL in your podcast hosting platform
                        (Spotify for Podcasters, Apple Podcasts Connect, etc.)
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              <div className="space-y-3">
                <Input
                  id="rss_url"
                  type="url"
                  value={rssUrl}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  placeholder="https://feeds.example.com/your-podcast"
                  className="h-12 text-lg"
                  onKeyPress={(e) => e.key === 'Enter' && handleValidate()}
                  disabled={isValidating || state.isLoading}
                />
                <Button
                  onClick={handleValidate}
                  disabled={!rssUrl || isValidating || state.isLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 h-12"
                >
                  {isValidating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Validating...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Validate RSS Feed
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Validation Results */}
            {isValid === true && podcastData !== null && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-green-50 border border-green-200 rounded-lg"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-green-900 mb-1">Valid RSS Feed!</h3>
                    <p className="text-green-800 font-medium">{podcastData?.title}</p>
                    {podcastData?.description && (
                      <p className="text-green-700 text-sm mt-1 line-clamp-2">
                        {podcastData.description}
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {isValid === false && error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Helper Text */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">Where to find your RSS feed:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• <strong>Spotify for Podcasters:</strong> Settings → Distribution</li>
                <li>• <strong>Apple Podcasts Connect:</strong> Your podcast → RSS Feed</li>
                <li>• <strong>Google Podcasts Manager:</strong> Feed details</li>
                <li>• <strong>Anchor:</strong> Settings → RSS Feed</li>
              </ul>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button
                variant="outline"
                onClick={() => navigate("/")}
                className="flex items-center gap-2"
                disabled={state.isLoading}
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
              <Button
                onClick={handleContinue}
                disabled={!isValid || !podcastData || state.isLoading}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 flex items-center gap-2"
              >
                {state.isLoading ? "Creating..." : "Continue"}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}