import React, { useState } from "react";
import { useNavigate } from "react-router";
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
  const { createPodcast, state } = useApp();
  
  const [rssUrl, setRssUrl] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [podcastData, setPodcastData] = useState<any>(null);

  const validateRSSFeed = async (url: string) => {
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
    } catch (error: any) {
      setIsValid(false);
      setError("Unable to validate RSS feed. Please check the URL and try again.");
    }
    setIsValidating(false);
  };

  const handleContinue = async () => {
    if (!podcastData) return;

    try {
      await createPodcast(podcastData);
      navigate("/onboarding/voice-sample");
    } catch (error: any) {
      setError(error.message || "Error creating podcast. Please try again.");
    }
  };

  const handleUrlChange = (value: string) => {
    setRssUrl(value);
    setIsValid(null);
    setError("");
    setPodcastData(null);
  };

  const handleValidate = () => {
    validateRSSFeed(rssUrl);
  };

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
            {isValid === true && podcastData && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-green-50 border border-green-200 rounded-lg"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-green-900 mb-1">Valid RSS Feed!</h3>
                    <p className="text-green-800 font-medium">{podcastData.title}</p>
                    {podcastData.description && (
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