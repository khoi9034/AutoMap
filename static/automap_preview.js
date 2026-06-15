(function () {
  const statusNode = document.getElementById("preview-status");
  const mapNode = document.getElementById("automap-preview-map");
  const configUrl = window.AUTOMAP_PREVIEW_CONFIG_URL || "/api/preview-config";

  function setStatus(message, isWarning) {
    if (!statusNode) return;
    statusNode.textContent = message;
    statusNode.classList.toggle("warning", Boolean(isWarning));
  }

  function normalizeOpacity(value) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return Math.max(0, Math.min(1, parsed));
    }
    return 1;
  }

  function extentFromConfig(Extent, extentConfig) {
    if (!extentConfig || typeof extentConfig !== "object") return null;
    const required = ["xmin", "ymin", "xmax", "ymax"];
    if (!required.every((key) => Number.isFinite(Number(extentConfig[key])))) {
      return null;
    }
    return new Extent({
      xmin: Number(extentConfig.xmin),
      ymin: Number(extentConfig.ymin),
      xmax: Number(extentConfig.xmax),
      ymax: Number(extentConfig.ymax),
      spatialReference: extentConfig.spatialReference || { wkid: 4326 },
    });
  }

  function layerFromConfig(layerConfig, MapImageLayer, FeatureLayer) {
    const title = layerConfig.title || "AutoMap Layer";
    const visible = layerConfig.visibility !== false;
    const opacity = normalizeOpacity(layerConfig.opacity);
    const definitionExpression = layerConfig.definition_expression || undefined;

    if (layerConfig.preview_type === "feature_layer") {
      return new FeatureLayer({
        url: layerConfig.layer_url || layerConfig.url,
        title,
        visible,
        opacity,
        definitionExpression,
        popupEnabled: true,
      });
    }

    if (layerConfig.preview_type === "map_image_sublayer") {
      if (!layerConfig.service_url || layerConfig.layer_id === null || layerConfig.layer_id === undefined) {
        return null;
      }
      return new MapImageLayer({
        url: layerConfig.service_url,
        title,
        visible,
        opacity,
        sublayers: [
          {
            id: layerConfig.layer_id,
            title,
            visible,
            opacity,
            definitionExpression,
          },
        ],
      });
    }

    if (layerConfig.preview_type === "map_image_layer" && (layerConfig.service_url || layerConfig.url)) {
      return new MapImageLayer({
        url: layerConfig.service_url || layerConfig.url,
        title,
        visible,
        opacity,
      });
    }

    return null;
  }

  async function loadConfig() {
    const response = await fetch(configUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`Preview config failed: ${response.status}`);
    }
    return response.json();
  }

  function bootPreview(config) {
    window.require(
      ["esri/Map", "esri/views/MapView", "esri/layers/MapImageLayer", "esri/layers/FeatureLayer", "esri/geometry/Extent"],
      function (Map, MapView, MapImageLayer, FeatureLayer, Extent) {
        const map = new Map({ basemap: "gray-vector" });
        const skipped = [];
        const layers = (config.operational_layers || [])
          .map((layerConfig) => {
            const layer = layerFromConfig(layerConfig, MapImageLayer, FeatureLayer);
            if (!layer) skipped.push(layerConfig.title || layerConfig.layer_key || "Untitled layer");
            return layer;
          })
          .filter(Boolean);

        map.layers.addMany(layers);

        const extent = extentFromConfig(Extent, config.initial_extent);
        const viewOptions = {
          container: mapNode,
          map,
          zoom: 10,
          center: [-80.58, 35.39],
        };
        if (extent) {
          viewOptions.extent = extent;
        }
        const view = new MapView(viewOptions);

        view.when(function () {
          const layerCount = layers.length;
          const skipMessage = skipped.length ? ` ${skipped.length} layer(s) could not be previewed.` : "";
          setStatus(`Preview loaded with ${layerCount} layer(s).${skipMessage}`, Boolean(skipped.length));
        }).catch(function (error) {
          setStatus(`Preview could not initialize: ${error.message}`, true);
        });
      }
    );
  }

  if (!mapNode) return;
  if (typeof window.require !== "function") {
    setStatus("ArcGIS Maps SDK did not load. Check network access and refresh.", true);
    return;
  }

  loadConfig()
    .then(bootPreview)
    .catch(function (error) {
      setStatus(error.message, true);
    });
})();
