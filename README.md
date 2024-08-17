Datasource
https://github.com/grafana/grafana/issues/89516

if (selectedQs.some(wildcard => wildcard === "$__all")) {
  var allQueue = allQueues[0].options.filter(q => q.text !== "All").map(queue => queue.value);
  allQueue.forEach(processQueue => {
    metricsPromises.push(options.targets.map(target => {
      target.qmetric = processQueue;
      target.queue = target.metric.replace('root', target.qmetric);
      return getYarnAppIdData(target);
    }));
  });
} else {
  // All selected queues.
  selectedQs.forEach(processQueue => {
    metricsPromises.push(options.targets.map(target => {
      target.qmetric = processQueue;
      target.queue = target.metric.replace('root', target.qmetric);
      return getYarnAppIdData(target);
    }));
  });
}
