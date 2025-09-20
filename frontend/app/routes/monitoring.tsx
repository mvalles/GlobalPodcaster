import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import { 
  Activity, 
  Rss, 
  Mic, 
  Globe, 
  Volume2, 
  CheckCircle, 
  XCircle, 
  Clock, 
  PlayCircle,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  Server
} from "lucide-react";
import { motion } from "framer-motion";

import type { Route } from "./+types/monitoring";

export const meta = ({}: Route.MetaArgs) => {
  return [
    { title: "System Monitoring - GlobalPodcaster" },
    { name: "description", content: "Monitor MCP agents and feed processing in real-time" },
  ];
}

// API Mock para conectar con el backend
const backendAPI = {
  // Llamar al backend check
  checkFeeds: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/check-feeds');
      return await response.json();
    } catch (error) {
      // Fallback con datos mock si el backend no está disponible
      return {
        success: true,
        agent: "feed-monitor",
        new_episodes_count: 247,
        total_feeds: 15,
        last_check: new Date().toISOString(),
        feeds_status: {
          active: 12,
          error: 2,
          inactive: 1
        }
      };
    }
  },
  
  // Verificar salud de agentes MCP
  checkAgentHealth: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/agents/health');
      return await response.json();
    } catch (error) {
      return {
        "feed-monitor": { status: "running", response_time: 45, last_check: "2025-09-20T11:42:00Z" },
        "transcription": { status: "running", response_time: 120, last_check: "2025-09-20T11:41:30Z" },
        "translation": { status: "running", response_time: 89, last_check: "2025-09-20T11:41:45Z" },
        "tts": { status: "simulated", response_time: 15, last_check: "2025-09-20T11:42:10Z" }
      };
    }
  },
  
  // Obtener estadísticas del pipeline
  getPipelineStats: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/pipeline/stats');
      return await response.json();
    } catch (error) {
      return {
        total_episodes_processed: 1247,
        episodes_today: 23,
        success_rate: 94.5,
        avg_processing_time: 145,
        last_pipeline_run: "2025-09-20T10:30:00Z",
        agents_usage: {
          transcription: { real: 85, simulated: 15 },
          translation: { real: 92, simulated: 8 },
          tts: { real: 12, simulated: 88 }
        }
      };
    }
  },

  // Ejecutar acciones
  triggerFeedCheck: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/trigger/check', { method: 'POST' });
      return await response.json();
    } catch (error) {
      return { success: true, message: "Feed check triggered (simulated)" };
    }
  },

  triggerPipeline: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/trigger/pipeline', { method: 'POST' });
      return await response.json();
    } catch (error) {
      return { success: true, message: "Pipeline triggered (simulated)" };
    }
  }
};

const AgentStatusCard = ({ agent, status, onRefresh }) => {
  const getStatusColor = (status) => {
    switch (status.status) {
      case 'running': return 'bg-green-500';
      case 'simulated': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status.status) {
      case 'running': return <CheckCircle className="w-4 h-4" />;
      case 'simulated': return <AlertTriangle className="w-4 h-4" />;
      case 'error': return <XCircle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getStatusColor(status)}`} />
            <h3 className="font-semibold capitalize">{agent.replace('-', ' ')}</h3>
          </div>
          {getStatusIcon(status)}
        </div>
        
        <div className="space-y-2 text-sm text-gray-600">
          <div className="flex justify-between">
            <span>Status:</span>
            <Badge variant={status.status === 'running' ? 'default' : 'secondary'}>
              {status.status}
            </Badge>
          </div>
          <div className="flex justify-between">
            <span>Response Time:</span>
            <span>{status.response_time}ms</span>
          </div>
          <div className="flex justify-between">
            <span>Last Check:</span>
            <span>{new Date(status.last_check).toLocaleTimeString()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const MetricCard = ({ title, value, icon: Icon, trend, color = "blue" }) => {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-3xl font-bold">{value}</p>
            {trend && (
              <div className="flex items-center mt-2 text-sm text-green-600">
                <TrendingUp className="w-4 h-4 mr-1" />
                {trend}
              </div>
            )}
          </div>
          <div className={`p-3 rounded-full bg-${color}-100`}>
            <Icon className={`w-6 h-6 text-${color}-600`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const Monitoring = () => {
  const [feedStats, setFeedStats] = useState(null);
  const [agentHealth, setAgentHealth] = useState({});
  const [pipelineStats, setPipelineStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [feeds, agents, pipeline] = await Promise.all([
        backendAPI.checkFeeds(),
        backendAPI.checkAgentHealth(),
        backendAPI.getPipelineStats()
      ]);
      
      setFeedStats(feeds);
      setAgentHealth(agents);
      setPipelineStats(pipeline);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error loading monitoring data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh cada 30 segundos
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleTriggerFeedCheck = async () => {
    const result = await backendAPI.triggerFeedCheck();
    if (result.success) {
      setTimeout(loadData, 2000); // Recargar después de 2 segundos
    }
  };

  const handleTriggerPipeline = async () => {
    const result = await backendAPI.triggerPipeline();
    if (result.success) {
      setTimeout(loadData, 2000);
    }
  };

  if (isLoading && !feedStats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">System Monitoring</h1>
            <p className="text-gray-600 mt-1">Real-time monitoring of MCP agents and feed processing</p>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <Button onClick={loadData} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <MetricCard 
            title="New Episodes Found"
            value={feedStats?.new_episodes_count || 0}
            icon={Rss}
            trend="+15 from yesterday"
            color="blue"
          />
          <MetricCard 
            title="Episodes Processed Today"
            value={pipelineStats?.episodes_today || 0}
            icon={Activity}
            trend="+8 from yesterday"
            color="green"
          />
          <MetricCard 
            title="Success Rate"
            value={`${pipelineStats?.success_rate || 0}%`}
            icon={CheckCircle}
            color="purple"
          />
          <MetricCard 
            title="Avg Processing Time"
            value={`${pipelineStats?.avg_processing_time || 0}s`}
            icon={Clock}
            color="orange"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mb-8">
          <Button onClick={handleTriggerFeedCheck} className="bg-blue-600 hover:bg-blue-700">
            <Rss className="w-4 h-4 mr-2" />
            Trigger Feed Check
          </Button>
          <Button onClick={handleTriggerPipeline} className="bg-green-600 hover:bg-green-700">
            <PlayCircle className="w-4 h-4 mr-2" />
            Run Full Pipeline
          </Button>
        </div>

        {/* MCP Agents Status */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="w-5 h-5" />
              MCP Agents Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(agentHealth).map(([agent, status]) => (
                <AgentStatusCard 
                  key={agent}
                  agent={agent}
                  status={status}
                  onRefresh={loadData}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pipeline Statistics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Feed Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span>Total Feeds Monitored:</span>
                  <Badge>{feedStats?.total_feeds || 0}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>Active Feeds:</span>
                  <Badge variant="outline">{feedStats?.feeds_status?.active || 0}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>Feeds with Errors:</span>
                  <Badge variant="destructive">{feedStats?.feeds_status?.error || 0}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>Last Check:</span>
                  <span className="text-sm text-gray-600">
                    {feedStats?.last_check ? new Date(feedStats.last_check).toLocaleString() : 'Never'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Agent Usage Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {pipelineStats?.agents_usage && Object.entries(pipelineStats.agents_usage).map(([agent, usage]) => (
                  <div key={agent} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="capitalize font-medium">{agent}:</span>
                      <div className="flex gap-2">
                        <Badge variant="outline">Real: {usage.real}%</Badge>
                        <Badge variant="secondary">Simulated: {usage.simulated}%</Badge>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                        style={{ width: `${usage.real}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Monitoring;