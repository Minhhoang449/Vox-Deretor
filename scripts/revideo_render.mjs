import path from 'node:path';
import {createRequire} from 'node:module';

const revideoRoot = path.resolve(process.env.REVIDEO_ROOT || 'D:/Coder/Revideo');
const projectRoot = path.resolve(process.env.REVIDEO_PROJECT_ROOT || process.cwd());
const publicDir = path.resolve(process.env.REVIDEO_PUBLIC_DIR || path.join(projectRoot, 'public'));
const outFile = path.resolve(process.env.REVIDEO_OUT_FILE || path.join(projectRoot, 'visuals.mp4'));
const require = createRequire(path.join(revideoRoot, 'package.json'));
const fs = require('node:fs');
const configuredChromePath = process.env.REVIDEO_CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH;
const chromeCandidates = configuredChromePath
  ? [configuredChromePath]
  : process.platform === 'win32'
    ? [
        path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe'),
        process.env['ProgramFiles(x86)'] && path.join(process.env['ProgramFiles(x86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
        process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'),
      ].filter(Boolean)
    : [];
const chromePath = chromeCandidates.find((candidate) => fs.existsSync(candidate));
if (configuredChromePath && !chromePath) throw new Error(`Configured Revideo Chrome is missing: ${configuredChromePath}`);
const {renderVideo} = require(path.join(revideoRoot, 'node_modules', '@revideo', 'renderer'));
const ffmpegPath = process.env.REVIDEO_FFMPEG_PATH || path.join(revideoRoot, 'node_modules', '@ffmpeg-installer', 'win32-x64', 'ffmpeg.exe');
if (!fs.existsSync(ffmpegPath)) throw new Error(`Revideo FFmpeg is missing: ${ffmpegPath}`);
const postprocessFfmpegPath = require('@ffmpeg-installer/ffmpeg').path;
const postprocessFfprobePath = require('@ffprobe-installer/ffprobe').path;
process.env.REVIDEO_FFMPEG_PATH = ffmpegPath;
if (chromePath) console.log(`[revideo] Chromium executable: ${chromePath}`);

const cacheDir = path.join(projectRoot, '.cache', 'vite');
fs.mkdirSync(path.dirname(outFile), {recursive: true});
const progress = new Map();
const gpuAcceleration = process.env.REVIDEO_GPU_ACCELERATION !== 'false';
process.chdir(projectRoot);
if (gpuAcceleration) console.log('[revideo] Chromium GPU acceleration enabled; FFmpeg codec:', process.env.REVIDEO_VIDEO_CODEC || 'default');
const result = await renderVideo({
  projectFile: './src/project.ts',
  settings: {
    outDir: path.dirname(outFile),
    outFile: path.basename(outFile),
    workers: Math.max(1, Number.parseInt(process.env.REVIDEO_WORKERS || '2', 10)),
    logProgress: false,
    ffmpeg: {
      ffmpegPath: postprocessFfmpegPath,
      ffprobePath: postprocessFfprobePath,
    },
    progressCallback: (worker, value) => {
      const step = Math.floor(value * 20);
      if (progress.get(worker) !== step) {
        progress.set(worker, step);
        console.log(`[revideo] render ${step * 5}%`);
      }
    },
    projectSettings: {exporter: {name: '@revideo/core/ffmpeg', options: {format: 'mp4'}}},
    puppeteer: {
      ...(chromePath ? {executablePath: chromePath} : {}),
      args: gpuAcceleration ? [
        '--enable-gpu',
        '--ignore-gpu-blocklist',
        '--enable-accelerated-2d-canvas',
        '--use-angle=d3d11',
        '--enable-webgl',
      ] : [],
    },
    viteConfig: {
      publicDir,
      cacheDir,
      resolve: {
        alias: [
          {find: /^@revideo\/renderer/, replacement: path.join(revideoRoot, 'packages', 'renderer')},
          {find: /^@revideo\/core$/, replacement: path.join(revideoRoot, 'packages', 'core', 'lib', 'index.js')},
          {find: /^@revideo\/2d$/, replacement: path.join(revideoRoot, 'packages', '2d', 'lib', 'index.js')},
        ],
      },
      server: {fs: {allow: [projectRoot, publicDir, revideoRoot]}},
    },
  },
});
console.log(`[revideo] done ${result?.video ?? result ?? outFile}`);
