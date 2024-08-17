Datasource
https://github.com/grafana/grafana/issues/89516

```
if (getTemplateSrv().getVariables()[1] && getTemplateSrv().getVariables()[1].name === "hosts") {
  let splitHosts = [];
  let allHosts;
  if (getTemplateSrv().getVariableWithName('hosts').current.text === "All") {
    allHosts = getTemplateSrv().getVariableWithName('hosts').options
      .filter(hostName => hostName.text !== "All")
      .map(hostVal => hostVal.value);
  }
  else {
    allHosts = getTemplateSrv().getVariableWithName('hosts').current.text.split(' + ');
  }
  while (allHosts.length > 0) {
    splitHosts.push(allHosts.splice(0,50));
  }
  splitHosts.forEach(splitHost => {
    metricsPromises.push(options.targets.map(target => {
      target.templatedHost = splitHost.join(',');
      return getAllHostData(target);
    }));
  });
}
```
