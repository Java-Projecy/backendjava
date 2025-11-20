package com.elecciones.backend.controller;

import com.elecciones.backend.model.VotoPresidencial;
import com.elecciones.backend.service.VotoPresidencialService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/data/presidential-votes")

public class VotoPresidencialController {

    private final VotoPresidencialService service;

    public VotoPresidencialController(VotoPresidencialService service) {
        this.service = service;
    }

    @GetMapping
    public List<VotoPresidencial> getAll() {
        return service.getAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<VotoPresidencial> getById(@PathVariable UUID id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public VotoPresidencial create(@RequestBody VotoPresidencial voto) {
        return service.save(voto);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable UUID id) {
        service.delete(id);
    }
}
