{{flutter_js}}
{{flutter_build_config}}
_flutter.loader.load({
  onEntrypointLoaded: async function(engineInitializer) {
    const engine = await engineInitializer.initializeEngine();
    document.getElementById('app-loader')?.remove();
    await engine.runApp();
  }
});
