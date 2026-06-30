import React from 'react';
import { useApp } from '../context/AppContext';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from 'recharts';
import { FileUp, Sparkles, CheckSquare, RefreshCw, Star, Info } from 'lucide-react';

export default function Analytics() {
  const { projects } = useApp();

  // Compute metrics from current projects list
  const totalProjects = projects.length;
  const completedProjects = projects.filter(p => p.status === 'COMPLETED');
  
  // Aggregate details
  let totalRequirements = 0;
  let totalStories = 0;
  let approvedStoriesCount = 0;
  let regeneratedCount = 0;
  
  completedProjects.forEach(p => {
    totalRequirements += p.summary?.totalRequirements || 0;
    totalStories += p.stories?.length || 0;
    approvedStoriesCount += p.stories?.filter(s => s.status === 'Approved').length || 0;
    regeneratedCount += p.stories?.filter(s => s.status === 'Needs Review' || s.validation_results?.quality_score > 90).length || 0;
  });

  // Default mock fallback values if user has no completed projects
  const displayRequirements = totalRequirements || 24;
  const displayStories = totalStories || 18;
  const displayApproved = approvedStoriesCount || 14;
  const displayRegen = regeneratedCount || 3;
  const displayConfidence = 91.4;

  // Chart 1: Stories by Epic / Module
  const epicCounts = {};
  completedProjects.forEach(p => {
    p.stories?.forEach(s => {
      epicCounts[s.epic] = (epicCounts[s.epic] || 0) + 1;
    });
  });
  
  const moduleData = Object.keys(epicCounts).length > 0 
    ? Object.keys(epicCounts).map(name => ({ name, count: epicCounts[name] }))
    : [
        { name: 'Authentication', count: 4 },
        { name: 'Billing', count: 3 },
        { name: 'Notifications', count: 6 },
        { name: 'Dashboard', count: 2 },
        { name: 'API Core', count: 3 }
      ];

  // Chart 2: Priority Distribution
  const priorityCounts = { High: 0, Medium: 0, Low: 0 };
  completedProjects.forEach(p => {
    p.stories?.forEach(s => {
      const prio = s.priority || 'Medium';
      if (priorityCounts[prio] !== undefined) priorityCounts[prio]++;
    });
  });

  const priorityData = (priorityCounts.High || priorityCounts.Medium || priorityCounts.Low)
    ? [
        { name: 'High', value: priorityCounts.High },
        { name: 'Medium', value: priorityCounts.Medium },
        { name: 'Low', value: priorityCounts.Low }
      ]
    : [
        { name: 'High', value: 5 },
        { name: 'Medium', value: 9 },
        { name: 'Low', value: 4 }
      ];

  // Chart 3: Approval Percentage over projects
  const approvalHistoryData = completedProjects.length > 0
    ? completedProjects.map((p, idx) => {
        const approved = p.stories?.filter(s => s.status === 'Approved').length || 0;
        const total = p.stories?.length || 1;
        return {
          name: p.name.substring(0, 12) + '...',
          percentage: Math.round((approved / total) * 100)
        };
      })
    : [
        { name: 'Proj-1', percentage: 75 },
        { name: 'Proj-2', percentage: 88 },
        { name: 'Proj-3', percentage: 92 },
        { name: 'Proj-4', percentage: 100 }
      ];

  // Chart 4: Processing Time in seconds
  const processingTimeData = [
    { name: '100 lines', seconds: 12 },
    { name: '300 lines', seconds: 18 },
    { name: '500 lines', seconds: 26 },
    { name: '800 lines', seconds: 38 },
    { name: '1200 lines', seconds: 54 }
  ];

  const PRIORITY_COLORS = ['#ef4444', '#f97316', '#64748b'];
  const GRADIENT_COLORS = ['#6366f1', '#10b981', '#3b82f6', '#8b5cf6', '#f43f5e'];

  return (
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">System Performance & Analytics</h2>
        <p className="text-xs text-slate-400 mt-1">Monitor ingestion counts, pipeline runs, approval velocities, and average quality scores.</p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {/* Card 1 */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-4 flex items-center space-x-4">
          <div className="rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
            <FileUp size={20} />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ingests</span>
            <div className="text-lg font-bold text-white mt-0.5">{displayRequirements}</div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-4 flex items-center space-x-4">
          <div className="rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
            <Sparkles size={20} />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Stories</span>
            <div className="text-lg font-bold text-white mt-0.5">{displayStories}</div>
          </div>
        </div>

        {/* Card 3 */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-4 flex items-center space-x-4">
          <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-400">
            <CheckSquare size={20} />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Approved</span>
            <div className="text-lg font-bold text-white mt-0.5">{displayApproved}</div>
          </div>
        </div>

        {/* Card 4 */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-4 flex items-center space-x-4">
          <div className="rounded-lg bg-orange-500/10 p-2.5 text-orange-400">
            <RefreshCw size={20} />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Refined</span>
            <div className="text-lg font-bold text-white mt-0.5">{displayRegen}</div>
          </div>
        </div>

        {/* Card 5 */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-4 flex items-center space-x-4 col-span-2 md:col-span-1">
          <div className="rounded-lg bg-amber-500/10 p-2.5 text-amber-400">
            <Star size={20} className="fill-amber-450/20" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Confidence</span>
            <div className="text-lg font-bold text-white mt-0.5">{displayConfidence}%</div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        
        {/* Chart 1: Stories by Epic */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-5">
          <h3 className="text-xs font-bold text-slate-205 uppercase tracking-wider mb-4">Stories Generated by Epic</h3>
          <div className="h-64 text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={moduleData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <XAxis dataKey="name" stroke="#475569" />
                <YAxis stroke="#475569" />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {moduleData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={GRADIENT_COLORS[index % GRADIENT_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Priority Distribution */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-5 flex flex-col justify-between">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-4">Priority Distribution</h3>
          <div className="h-56 text-xs flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={priorityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {priorityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PRIORITY_COLORS[index % PRIORITY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Legend */}
          <div className="flex justify-center space-x-6 text-[10px] font-semibold uppercase text-slate-500 mt-2">
            <div className="flex items-center"><span className="h-2.5 w-2.5 rounded-full bg-red-500 mr-2" />High</div>
            <div className="flex items-center"><span className="h-2.5 w-2.5 rounded-full bg-orange-500 mr-2" />Medium</div>
            <div className="flex items-center"><span className="h-2.5 w-2.5 rounded-full bg-slate-500 mr-2" />Low</div>
          </div>
        </div>

        {/* Chart 3: Approval Rates */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-5">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-4">Story Approval Rate (%)</h3>
          <div className="h-64 text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={approvalHistoryData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorApproval" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#475569" />
                <YAxis stroke="#475569" unit="%" />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                <Area type="monotone" dataKey="percentage" stroke="#10b981" fillOpacity={1} fill="url(#colorApproval)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Processing Times */}
        <div className="rounded-xl border border-slate-900 bg-slate-900/35 p-5">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-4">Extraction Processing Time vs Word Length</h3>
          <div className="h-64 text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={processingTimeData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <XAxis dataKey="name" stroke="#475569" />
                <YAxis stroke="#475569" unit="s" />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                <Legend />
                <Line type="monotone" dataKey="seconds" name="Seconds to Process" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
